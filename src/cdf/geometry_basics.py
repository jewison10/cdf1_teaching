"""Bauhaus chandelier: parametric geometry for Grasshopper (Rhino 8, Python 3).

Copy this into cdf1_teaching/src/cdf/geometry_basics.py (merge with existing code).

Master parameters
-----------------
tension (0..1) : character of the design, calm -> dramatic. Derives most values.
style   (0,1,2): 0 Kandinsky (form -> colour), 1 random primaries, 2 monochrome + lights
seed    (int)  : layout variation
follow  (0..1) : how much hangers lean with their ring (0 = gravity, 1 = rigid)
time    (deg)  : animation driver, 0..360 is exactly one seamless loop; tiers spin in alternating directions

Every derived value can be overridden by passing it explicitly.
"""
import math
import random

try:
    import Rhino.Geometry as rg  # pyright: ignore[reportMissingImports]  # Rhino-only; available inside Rhino / Grasshopper
except ImportError:
    rg = None  # lets VS Code import the file to test pure-Python parts such as derive_params

TOL = 0.001
COLOR_KEYS = ("red", "yellow", "blue", "black", "white", "bulb")
KANDINSKY = {"cube": "red", "cylinder": "blue", "prism": "yellow"}
SHAPES = ("cube", "cylinder", "prism")


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _lerp(a, b, t):
    return a + (b - a) * t


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _round(x):
    return int(math.floor(x + 0.5))


def _frame(origin, axis_z):
    """Plane at origin whose Z axis points along axis_z."""
    z = rg.Vector3d(axis_z)
    z.Unitize()
    x = rg.Vector3d.CrossProduct(rg.Vector3d.YAxis, z)
    if x.Length < 1e-6:
        x = rg.Vector3d.CrossProduct(rg.Vector3d.XAxis, z)
    x.Unitize()
    y = rg.Vector3d.CrossProduct(z, x)
    return rg.Plane(origin, x, y)


# ----------------------------------------------------------------------
# basic primitives (all built on a plane, extruded along plane Z)
# ----------------------------------------------------------------------
def make_box(plane, sx, sy, sz):
    """Box centred on the plane origin in x/y, extruded along plane Z by sz.

    Built the same way as the prism (capped extrusion of a closed rectangle),
    which is known to work in Rhino 8, instead of rg.Box(...).ToBrep().
    """
    pts = [
        plane.PointAt(-sx / 2.0, -sy / 2.0),
        plane.PointAt(sx / 2.0, -sy / 2.0),
        plane.PointAt(sx / 2.0, sy / 2.0),
        plane.PointAt(-sx / 2.0, sy / 2.0),
    ]
    pts.append(pts[0])
    srf = rg.Surface.CreateExtrusion(rg.PolylineCurve(pts), plane.ZAxis * sz)
    brep = srf.ToBrep()
    capped = brep.CapPlanarHoles(TOL)
    return capped if capped is not None else brep


def make_cylinder(plane, radius, height):
    return rg.Cylinder(rg.Circle(plane, radius), height).ToBrep(True, True)


def make_triangular_prism(plane, side, height):
    h = side * math.sqrt(3.0) / 2.0
    pts = [
        plane.PointAt(-side / 2.0, -h / 3.0),
        plane.PointAt(side / 2.0, -h / 3.0),
        plane.PointAt(0.0, 2.0 * h / 3.0),
    ]
    pts.append(pts[0])
    srf = rg.Surface.CreateExtrusion(rg.PolylineCurve(pts), plane.ZAxis * height)
    brep = srf.ToBrep()
    capped = brep.CapPlanarHoles(TOL)
    return capped if capped is not None else brep


def make_sphere(center, radius):
    return rg.Sphere(center, radius).ToBrep()


def make_rod(p0, p1, radius):
    v = p1 - p0
    length = v.Length
    if length < TOL:
        return None
    plane = rg.Plane(p0, v)
    return rg.Cylinder(rg.Circle(plane, radius), length).ToBrep(True, True)


def make_ring(plane, radius, tube):
    """Thin torus lying in the plane."""
    return rg.Torus(plane, radius, tube).ToRevSurface().ToBrep()


# ----------------------------------------------------------------------
# parameter relationships
# ----------------------------------------------------------------------
def derive_params(tension):
    """Every value below is a function of the single master value `tension`."""
    t = _clamp(tension)
    return {
        "tiers": 4,                          # fixed: every variant has the same four rings
        "amp": _lerp(0.0, 3.0, t * t),       # string-length variation (calm for a while, then grows fast)
        "freq": 1 + _round(t * 5),           # high/low points per ring
        "tilt": _lerp(0.0, 30.0, t),         # ring tilt in degrees
        "spin_speed": _lerp(0.2, 1.5, t),
        "items": _round(_lerp(4, 12, t)),    # hangers on the outer tier
        "decay": _lerp(1.0, 0.75, t),        # size shrink per tier
        "gap": _lerp(80.0, 60.0, t),         # vertical spacing between tiers
        "follow": _lerp(0.3, 1.0, t),
    }


def _pick(override, derived):
    return derived if override is None else override


# ----------------------------------------------------------------------
# main composition
# ----------------------------------------------------------------------
def bauhaus_chandelier(
    tension=0.5,
    style=0,
    seed=7,
    follow=None,
    time=0.0,
    tiers=None,
    tilt=None,
    wave_amp=None,
    wave_freq=None,
    spin_speed=None,
    items=None,
    gap=None,
    drop_base=26.0,
    size_base=15.0,
    bulb_ratio=0.2,
    ring_min=30.0,
    ring_max=90.0,
    top_drop=60.0,
    w_cube=1.0,
    w_cylinder=1.0,
    w_prism=1.0,
    ring_tube=1.0,
    string_radius=0.25,
    count_scale=1.0,
    spoke_step=2,
    spacing=2.2,
):
    """Return (dict {colour: [Brep]}, info string)."""
    p = derive_params(tension)
    n_tiers = max(1, int(_pick(tiers, p["tiers"])))
    tilt = _clamp(_pick(tilt, p["tilt"]), 0.0, 80.0)
    amp = _pick(wave_amp, p["amp"])
    freq = max(1, int(_pick(wave_freq, p["freq"])))
    speed = _pick(spin_speed, p["spin_speed"])
    n_items = max(3, int(_pick(items, p["items"])))
    gap = _pick(gap, p["gap"])
    follow = _clamp(_pick(follow, p["follow"]))
    decay = p["decay"]
    style = int(style)

    out = {k: [] for k in COLOR_KEYS}
    shape_count = {"cube": 0, "cylinder": 0, "prism": 0, "bulb": 0}
    failed = [0]  # geometry calls that returned None
    down = rg.Vector3d(0, 0, -1)
    weights = [max(0.0, w_cube), max(0.0, w_cylinder), max(0.0, w_prism)]
    total_w = sum(weights) or 1.0

    # canopy + central stem (ceiling at z = 0)
    canopy_plane = rg.Plane(rg.Point3d(0, 0, -3), rg.Vector3d.XAxis, rg.Vector3d.YAxis)
    out["black"].append(make_cylinder(canopy_plane, 8.0, 3.0))
    last_z = -(top_drop + (n_tiers - 1) * gap)
    stem = make_rod(rg.Point3d(0, 0, 0), rg.Point3d(0, 0, last_z), 1.2)
    if stem:
        out["black"].append(stem)

    for k in range(n_tiers):
        rand = random.Random(int(seed) * 1000 + k)  # per-tier stream: adding tiers never reshuffles earlier ones
        direction = 1.0 if k % 2 == 0 else -1.0     # alternating spin and tilt direction
        centre = rg.Point3d(0, 0, -(top_drop + k * gap))

        # number and size of hangers first: the ring is then fitted to them
        size = max(6.0, size_base * (decay ** k))
        n = max(3, _round(n_items * (0.55 + 0.45 * (k + 1.0) / n_tiers)))

        # ring radius follows the hanger count:
        #  - base radius from ring_min..ring_max, scaled by (items/8)^(0.5*count_scale)
        #  - never smaller than needed to give each hanger `spacing` x its size of arc length
        base_r = _lerp(ring_min, ring_max, k / (n_tiers - 1.0)) if n_tiers > 1 else ring_min
        base_r *= (n_items / 8.0) ** (0.5 * count_scale)
        radius = max(base_r, n * size * spacing / (2.0 * math.pi))

        # ring plane: tilted about an axis that precesses with time
        plane = rg.Plane(centre, rg.Vector3d.XAxis, rg.Vector3d.YAxis)
        tilt_dir = math.radians(k * 70.0 + time * direction)  # exactly 1 full precession turn per 360 of time
        plane.Rotate(math.radians(tilt), rg.Vector3d(math.cos(tilt_dir), math.sin(tilt_dir), 0), centre)

        # whole number of turns per loop (outer tiers turn fewer times) -> frame at time=360 equals frame at time=0
        turns = max(1, _round(speed * 2.0 / (1.0 + 0.4 * k)))
        spin = math.radians(direction * turns * time)
        out["black"].append(make_ring(plane, radius, ring_tube))

        # spokes end exactly where hangers attach (every `step`-th hanger, never fewer than 3 spokes),
        # so adding hangers adds spokes and the strings visibly hang from the frame
        step = max(1, min(int(spoke_step), n // 3))
        for i in range(0, n, step):
            a_i = 2.0 * math.pi * i / n + k * 0.5 + spin
            pt = plane.PointAt(radius * math.cos(a_i), radius * math.sin(a_i))
            rod = make_rod(centre, pt, 0.6)
            if rod:
                out["black"].append(rod)

        # hanger direction: blend of gravity and ring normal (pointing down)
        ring_down = rg.Vector3d(plane.ZAxis)
        ring_down.Reverse()
        hang = down * (1.0 - follow) + ring_down * follow
        hang.Unitize()

        for i in range(n):
            # fixed draw order per item
            bulb_r = rand.random()
            shape_r = rand.random()
            color_r = rand.random()
            twist_r = rand.random() * 2.0 * math.pi

            theta0 = 2.0 * math.pi * i / n + k * 0.5
            theta = theta0 + spin
            P = plane.PointAt(radius * math.cos(theta), radius * math.sin(theta))

            # drop length follows a wave over the world angle, so high/low points stay put while items spin through them
            wave = math.sin(freq * theta + k * 1.3)
            drop = drop_base * (1.0 + _clamp(amp / 3.0 * 0.8) * wave)
            E = P + hang * drop

            string = make_rod(P, E, string_radius)
            if string:
                out["black"].append(string)

            if bulb_r < bulb_ratio:
                shape_count["bulb"] += 1
                out["bulb"].append(make_sphere(E + hang * (0.5 * size), 0.5 * size))
                continue

            shape, acc = SHAPES[-1], 0.0
            for name, wi in zip(SHAPES, weights):
                acc += wi / total_w
                if shape_r <= acc:
                    shape = name
                    break
            sp = _frame(E, hang)
            sp.Rotate(twist_r + spin, sp.ZAxis, E)

            if shape == "cube":
                brep = make_box(sp, size, size, size)
            elif shape == "cylinder":
                brep = make_cylinder(sp, 0.55 * size, 0.6 * size)
            else:
                brep = make_triangular_prism(sp, 1.1 * size, 0.6 * size)

            shape_count[shape] += 1
            if brep is None:
                failed[0] += 1
            if style == 0:
                colour = KANDINSKY[shape]
            elif style == 1:
                colour = ("red", "yellow", "blue")[min(2, int(color_r * 3))]
            else:
                colour = "white" if color_r < 0.5 else "black"
            if brep is not None:
                out[colour].append(brep)

    info = (
        "tension {:.2f} | style {} | tiers {} | hangers on outer tier {} | wave freq {} amp {:.2f} | "
        "tilt {:.0f} deg | follow {:.2f} | spin {:.2f}\n"
        "cubes {} | cylinders {} | prisms {} | bulbs {} | FAILED shapes {}\n"
        "outputs -> red {} | yellow {} | blue {} | black(frame) {} | white {} | bulb {}"
    ).format(
        tension, style, n_tiers, n_items, freq, amp, tilt, follow, speed,
        shape_count["cube"], shape_count["cylinder"], shape_count["prism"], shape_count["bulb"], failed[0],
        len(out["red"]), len(out["yellow"]), len(out["blue"]), len(out["black"]), len(out["white"]), len(out["bulb"]),
    )
    return out, info