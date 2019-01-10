# -*- coding: utf-8 -*-
""" pyxs.geometry_2d.py

(C) 2017 Dima Pustakhod and contributors
"""
import math


from klayout_pyxs import Box
from klayout_pyxs import EP_
from klayout_pyxs import Point
from klayout_pyxs import Polygon
from klayout_pyxs import Trans

from klayout_pyxs.layer_parameters import string_to_layer_info
from klayout_pyxs.misc import info, print_info, int_floor, make_iterable


class EdgeProcessor(EP_):
    """
    Problems: empty polygon arrays produce errors with boolean_to_polygon
    because RBA does not recognize the empty array as an array of polygons
    and then there is an ambiguity between the edge-input and polygon input
    variants. Thus this extension which checks for empty input and performs
    some default operation
    """
    def boolean_p2p(self, pa, pb, mode, rh=True, mc=True):
        """ Boolean operation for a set of given polygons, creating polygons

        This method computes the result for the given boolean operation on
        two sets of polygons. This method produces polygons on output and
        allows to fine-tune the parameters for that purpose.

        This is a convenience method that bundles filling of the edges,
        processing with a Boolean operator and puts the result into an output
        vector.

        Parameters
        ----------
        pa : list of Polygon
            the input polygons (first operand)
        pb : list of Polygon
            the input polygons (second operand)
        mode : int
            one of self.ModeANotB, self.ModeAnd, self.ModeBNotA,
            self.ModeOr, self.ModeXor
        rh : bool (optional)
            True, if holes should be resolved into the hull
        mc : bool (optional)
            True, if touching corners should be resolved into less connected
            contours

        Returns
        -------
        res : list of Polygon
            The output polygons

        """
        return super().boolean_p2p(pa, pb, mode, rh, mc)

    def safe_boolean_to_polygon(self, pa, pb, mode, rh=True, mc=True):
        """ Applies boolean operation to two lists of polygons.

        Use of this method is deprecated. Use boolean_p2p instead

        Works safe in case any of input arrays is empty.

        Parameters
        ----------
        pa : list of Polygon
        pb : list of Polygon
        mode : int
        rh : bool (optional)
            resolve_holes
        mc : bool (optional)
            min_coherence

        Returns
        -------
        list of Polygon or []
        """
        n_pa, n_pb = len(pa), len(pb)  # number of polygons in pa and pb

        if n_pa > 0 and n_pb > 0:  # both pa and pb are not empty
            return self.boolean_to_polygon(pa, pb, mode, rh, mc)
        elif mode == self.ModeAnd:  # either pa and pb is empty, mode AND
            return []  # will be empty
        elif mode == self.ModeOr:
            if n_pa > 0:
                return pa
            else:
                return pb
        elif mode == self.ModeXor:
            if n_pa > 0:
                return pa
            else:
                return pb
        elif mode == self.ModeANotB:
            return pa
        elif mode == self.ModeBNotA:
            return pb
        else:
            return []

    def size_to_polygon(self, polygons, dx, dy, mode=2, rh=True, mc=True):
        """ Size the given polygons into polygons

        Use of this method is deprecated. Use size_p2p instead
        """
        return super().size_to_polygon(polygons, dx, dy, mode, rh, mc)

    @print_info(False)
    def size_p2p(self, polygons, dx, dy=0, mode=2, rh=True, mc=True):
        """ Size the given polygons into polygons

        Parameters
        ----------
        polygons : list of Polygon
            The input polygons
        dx : int
            The sizing value in x direction in dbu
        dy : int (optional)
            The sizing value in y direction in dbu
        mode : int (optional)
            The sizing mode. Allowed values from 1 to 5
        rh : bool (optional)
            True, if holes should be resolved into the hull
        mc : bool (optional)
            True, if touching corners should be resolved into less connected
            contours

        Returns
        -------
        res : list of Polygon
            The output polygons

        """
        info('    polys  = {}'.format(polygons))
        info('    dx = {}, dy = {}'.format(dx, dy))
        res = super().size_p2p(polygons, dx, dy, mode, rh, mc)
        info('    EP.size_p2p().res = {}'.format(res))
        return res


EP = EdgeProcessor
ep = EdgeProcessor()


def parse_grow_etch_args(method, into=[], through=[], on=[],
                         mode='square', material_cls=None):
    """
    Parameters
    ----------
    method : str
        'etch|grow'
    into : None or list (optional)
    on : None or list (optional)
    through : None or list (optional)
    mode : str (optional)
        'square|round|octagon'
    material_cls : type (optional)
        into, through, and on lists must contain instances of this type.

    Returns
    -------
    res : tuple
        into : None or list
        through : None or list
        on : None or list
        mode : str
            'square|round|octagon'

    """
    if into:
        into = make_iterable(into)
        for i in into:
            # should be MaterialData @@@
            if not isinstance(i, material_cls):
                raise TypeError("'{}' method: 'into' expects a material "
                                "parameter or an array of such. {} is given"
                                .format(method, type(i)))
    if on:
        on = make_iterable(on)
        for i in on:
            # should be MaterialData @@@
            if not isinstance(i, material_cls):
                raise TypeError("'{}' method: 'on' expects a material "
                                "parameter or an array of such".format(method))
    if through:
        through = make_iterable(through)
        for i in through:
            # should be MaterialData @@@
            if not isinstance(i, material_cls):
                raise TypeError("'{}' method: 'through' expects a material "
                                "parameter or an array of such".format(method))

    if on and (through or into):
        raise ValueError("'on' option cannot be combined with 'into' or "
                         "'through' option")

    if mode not in ('round', 'square', 'octagon'):
        raise ValueError("'{}' method: 'mode' should be 'round', 'square' or "
                         "'octagon'".format(method))

    return into, through, on, mode


class LayoutData(object):
    """ Class to manipulate masks, which is a 2d view.

    Layout data is a list of polygons.

    Attributes
    ----------
    self._polygons : list of Polygon
        In case of XSectionGenerator.layer() object, self._polygons
        contains shapes touching the ruler, top view of the mask
    """
    def __init__(self, polygons, xs):
        """ LayoutData constructor.

        Parameters
        ----------
        polygons : list of Polygon
            list of shapes contained in this LayoutData
        xs : XSectionGenerator

        """
        self._polygons = polygons
        self._xs = xs
        self._ep = ep

    def __str__(self):
        n_poly = self.n_poly

        s = 'LayoutData (n_polygons = {})'.format(n_poly)

        if n_poly > 0:
            s += ':'

        for pi in range(min(2, n_poly)):
            s += '\n    {}'.format(self._polygons[pi])
        return s

    def __repr__(self):
        s = '<LayoutData (n_polygons = {})>'.format(self.n_poly)
        return s

    @property
    def data(self):
        """
        Return
        ------
        data: list of Polygon
            polygons which constitute the mask
        """
        return self._polygons

    @data.setter
    def data(self, polygons):
        """
        Parameters
        ----------
        polygons: list of Polygon
            polygons to be saved in the mask
        """
        self._polygons = polygons

    def add(self, other):
        """ Add more polygons to the layout (OR).

        Parameters
        ----------
        other : LayoutData or list of Polygon

        """
        other_polygons = self._get_polygons(other)
        self._polygons = self._ep.boolean_p2p(
                self._polygons, other_polygons, EP.ModeOr)

    def and_(self, other):
        """ Calculate overlap of the mask with a list of polygons (AND).

        Parameters
        ----------
        other : LayoutData or list of Polygon

        Returns
        -------
        ld : LayoutData
        """
        other_polygons = self._get_polygons(other)
        return LayoutData(self._ep.boolean_p2p(
                self._polygons, other_polygons, EP.ModeAnd),
                          self._xs)

    def inverted(self):
        """ Calculate inversion of the mask.

        Total region is determined by self._xs.background().

        Returns
        -------
        ld : LayoutData
        """
        return LayoutData(self._ep.boolean_p2p(
                self._polygons, [Polygon(self._xs.background())], EP.ModeXor),
            self._xs)

    @print_info(False)
    def load(self, layout, cell, box, layer_spec):
        """ Load all shapes from the layer into self._polygons.

        The shapes are collected from layer defined by layer_spec. Only
        shapes touching the box are loaded. Box is effectively a ruler region.

        Parameters
        ----------
        layout : Layout
            layout
        cell : int
            cell's index
        box : Box
            The box of the ruler, enlarged in both directions.
            Only shapes touching this box will be collected
        layer_spec : str
            layer to be used
        """
        info('LD.load(..., box={}, layer_spec={})'.format(box, layer_spec))

        ls = string_to_layer_info(layer_spec)

        # look up the layer index with a given layer_spec in the current layout
        layer_index = None
        for li in layout.layer_indices():
            info("    li = {}".format(li))
            if layout.get_info(li).is_equivalent(ls):
                info("        layer_index = {}".format(li))
                layer_index = li
                break

        # collect polygons from the specified layer
        # all the shapes from the layout will be saved in self._polygons
        if layer_index is not None:
            info("    iterations:")
            shape_iter = layout.begin_shapes_touching(cell, layer_index, box)
            while not shape_iter.at_end():
                shape = shape_iter.shape()
                if shape.is_polygon() or shape.is_path() or shape.is_box():
                    self._polygons.append(
                            shape.polygon.transformed_cplx(shape_iter.itrans()))
                shape_iter.next()

        n_poly = self.n_poly
        info('    loaded polygon count: {}'.format(n_poly))
        if n_poly > 0:
            info('    loaded polygons:')
        for pi in range(min(2, n_poly)):
            info('        {}'.format(self._polygons[pi]))

        info('LD.load()\n')

    def mask(self, other):
        """ Mask current layout with external list of polygons (AND).

        Parameters
        ----------
        other : LayoutData or list of Polygon

        """
        other_polygons = self._get_polygons(other)
        self._polygons = self._ep.boolean_p2p(
                self._polygons, other_polygons, EP.ModeAnd)

    @property
    def n_poly(self):
        """
        Returns
        -------
        n_poly : int
            number of polygons contained in the mask

        """
        return len(self._polygons)

    def not_(self, other):
        """ Calculate difference with another list of polygons.

        Parameters
        ----------
        other : LayoutData or list of Polygon

        Returns
        -------
        ld : LayoutData
        """
        other_polygons = self._get_polygons(other)
        return LayoutData(self._ep.boolean_p2p(
                self._polygons, other_polygons, EP.ModeANotB),
                          self._xs)

    def or_(self, other):
        """ Calculate sum with another list of polygons (OR).
        Parameters
        ----------
        other : LayoutData or list of Polygon

        Returns
        -------
        ld : LayoutData
        """
        other_polygons = self._get_polygons(other)
        return LayoutData(self._ep.boolean_p2p(
                self._polygons, other_polygons, EP.ModeOr),
                          self._xs)

    def sized(self, dx, dy=None):
        """ Calculate a sized mask.

        Parameters
        ----------
        dx : float
            size change in x-direction in [um]
        dy : float (optional)
            size change in y-direction in [um]. Equals to dx by default.

        Returns
        -------
        ld : LayoutData
        """
        dy = dx if dy is None else dy
        ld = LayoutData(self._ep.size_p2p(self._polygons,
                                          int_floor(dx / self._xs.dbu + 0.5),
                                          int_floor(dy / self._xs.dbu + 0.5)),
                        self._xs)
        return ld

    def sub(self, other):
        """ Substract another list of polygons.

        Parameters
        ----------
        other : LayoutData or list of Polygon

        """
        other_polygons = self._get_polygons(other)
        self._polygons = self._ep.boolean_p2p(
                self._polygons, other_polygons, EP.ModeANotB)

    def transform(self, t):
        """ Transform mask with a transformation.

        Parameters
        ----------
        t : Trans
            transformation to be applied
        """
        self._polygons = [p.transformed(t) for p in self._polygons]

    def xor(self, other):
        """ Calculate XOR with another list of polygons.

        Parameters
        ----------
        other : LayoutData or list of Polygon

        Returns
        -------
        ld : LayoutData
        """
        other_polygons = self._get_polygons(other)
        return LayoutData(self._ep.boolean_p2p(
                self._polygons, other_polygons, EP.ModeXor),
                          self._xs)

    def close_gaps(self):
        """ Close gaps in self._polygons.

        Increase size of all polygons by 1 dbu in all directions.
        """
        sz = 1
        d = self._polygons
        d = self._ep.size_p2p(d, 0, sz)
        d = self._ep.size_p2p(d, 0, -sz)
        d = self._ep.size_p2p(d, sz, 0)
        d = self._ep.size_p2p(d, -sz, 0)
        self._polygons = d

    def remove_slivers(self):
        """ Remove slivers in self._polygons.
        """
        sz = 1
        d = self._polygons
        d = self._ep.size_p2p(d, 0, -sz)
        d = self._ep.size_p2p(d, 0, sz)
        d = self._ep.size_p2p(d, -sz, 0)
        d = self._ep.size_p2p(d, sz, 0)
        self._polygons = d

    @staticmethod
    def _get_polygons(l):
        if isinstance(l, LayoutData):
            return l.data
        elif isinstance(l, (tuple, list)):
            return l
        else:
            raise TypeError('l should be either an instance of LayoutData or '
                            'a list of Polygon. {} is given.'
                            .format(type(l)))


class MaterialData(LayoutData):
    """ Class to operate 2D cross-sections.

    Material data is a list of single

    """
    def __init__(self, polygons, xs, delta):
        """
        Parameters
        ----------
        polygons : list of Polygon
            list of shapes in cross-section
        xs: XSectionGenerator
            passed to LayoutData.__init__()
        delta : float
            the intrinsic height (required for mask data because there
            cannot be an infinitely small mask layer (in database units)
        """
        super().__init__(polygons, xs)  # LayoutData()
        self._delta = delta

    def __str__(self):
        n_poly = self.n_poly

        s = 'MaterialData (delta = {}, n_polygons = {})'.format(
            self._delta, n_poly)

        if n_poly > 0:
            s += ':'

        for pi in range(min(2, n_poly)):
            s += '\n    {}'.format(self._polygons[pi])
        return s

    def __repr__(self):
        s = '<MaterialData (delta = {}, n_polygons = {})>'.format(
            self._delta, self.n_poly)
        return s

    @print_info(False)
    def grow(self, z, xy=0.0, into=(), through=(), on=(), mode='square',
             taper=None, bias=None, buried=None):
        """
        Parameters
        ----------
        z : float
            height
        xy : float
            lateral
        mode : str
            'round|square|octagon'. The profile mode.
        taper : float
            The taper angle. This option specifies tapered mode and cannot
            be combined with :mode.
        bias : float
            Adjusts the profile by shifting it to the interior of the figure.
            Positive values will reduce the line width by twice the value.
        on : list of MaterialData (optional)
            A material or an array of materials onto which the material is
            deposited (selective grow). The default is "all". This option
            cannot be combined with ":into". With ":into", ":through" has the
            same effect than ":on".
        into : list of MaterialData (optional)
            Specifies a material or an array of materials that the new
            material should consume instead of growing upwards. This will
            make "grow" a "conversion" process like an implant step.
        through : list of MaterialData (optional)
            To be used together with ":into". Specifies a material or an array
            of materials to be used for selecting grow. Grow will happen
            starting on the interface of that material with air, pass
            through the "through" material (hence the name) and consume and
            convert the ":into" material below.
        buried : float
            Applies the conversion of material at the given depth below the
            mask level. This is intended to be used together with :into
            and allows modeling of deep implants. The value is the depth
            below the surface.

        """
        # parse the arguments
        info('    into={}'.format(into))
        into, through, on, mode = parse_grow_etch_args(
            'grow', into=into, through=through, on=on, mode=mode,
            material_cls=MaterialData)

        info('    into={}'.format(into))
        # produce the geometry of the new material
        d = self.produce_geom('grow', xy, z,
                              into, through, on,
                              taper, bias, mode, buried)

        # prepare the result
        # list of Polygon which are removed
        res = MaterialData(d, self._xs, 0)

        # consume material
        if into:
            for i in into:  # for each MaterialData
                i.sub(res)
                i.remove_slivers()
        else:
            self._xs.air().sub(res)  # remove air where material was added
            self._xs.air().remove_slivers()
        return res

    def etch(self, z, xy=0.0, into=(), through=(), mode='square',
             taper=None, bias=None, buried=None):
        """

        Parameters
        ----------
        z : float
            etch depth
        xy : float (optional)
            mask extension, lateral
        mode : str
            'round|square|octagon'. The profile mode.
        taper :	float
            The taper angle. This option specifies tapered mode and cannot
            be combined with mode.
        bias : float
            Adjusts the profile by shifting it to the interior of the
            figure. Positive values will reduce the line width by twice
            the value.
        into :	list of MaterialData (optional)
            A material or an array of materials into which the etch is
            performed. This specification is mandatory.
        through : list of MaterialData (optional)
            A material or an array of materials which form the selective
            material of the etch. The etch will happen only where this
            material interfaces with air and pass through this material
            (hence the name).
        buried : float
            Applies the etching at the given depth below the surface. This
            option allows to create cavities. It specifies the vertical
            displacement of the etch seed and there may be more applications
            for this feature.

        """
        # parse the arguments
        into, through, on, mode = parse_grow_etch_args(
            'etch', into=into, through=through, on=(), mode=mode,
            material_cls=MaterialData)

        if not into:
            raise ValueError("'etch' method: requires an 'into' specification")

        # prepare the result
        d = self.produce_geom('etch', xy, z,
                              into, through, on,
                              taper, bias, mode, buried)  # list of Polygon

        # produce the geometry of the etched material
        # list of Polygon which are removed
        res = MaterialData(d, self._xs, 0)

        # consume material and add to air
        if into:
            for i in into:  # for each MaterialData
                i.sub(res)
                i.remove_slivers()

        # Add air in place of the etched materials
        self._xs.air().add(res)
        self._xs.air().close_gaps()

    @print_info(False)
    def produce_geom(self, method, xy, z,
                     into, through, on,
                     taper, bias, mode, buried):
        """

        Parameters
        ----------
        method : str
        xy : float
            extension
        z : float
            height
        into : list of MaterialData
        through : list of MaterialData
        on : list of MaterialData
        taper : float
        bias : float
        mode : str
            'round|square|octagon'
        buried :

        Returns
        -------
        d : list of Polygon
        """
        info('    method={}, xy={}, z={}, \n'
             '    into={}, through={}, on={}, \n'
             '    taper={}, bias={}, mode={}, buried={})'
             .format(method, xy, z, into, through, on,
                     taper, bias, mode, buried))

        prebias = bias or 0.0

        if xy < 0.0:  # if size to be reduced,
            xy = -xy  #
            prebias += xy  # positive prebias

        if taper:
            d = z * math.tan(math.pi / 180.0 * taper)
            prebias += d - xy
            xy = d

        # determine the "into" material by joining the data of all "into" specs
        # or taking "air" if required.
        # into_data is a list of polygons from all `into` MaterialData
        # Finally we get a into_data, which is a list of Polygons
        if into:
            into_data = []
            for i in into:
                if len(into_data) == 0:
                    into_data = i.data
                else:
                    into_data = self._ep.boolean_p2p(i.data, into_data,
                                                     EP.ModeOr)
        else:
            # when deposit or grow is selected, into_data is self.air()
            into_data = self._xs.air().data

        info('    into_data = {}'.format(into_data))

        # determine the "through" material by joining the data of all
        # "through" specs
        # through_data is a list of polygons from all `through` MaterialData
        # Finally we get a through_data, which is a list of Polygons
        if through:
            through_data = []
            for i in through:
                if len(through_data) == 0:
                    through_data = i.data
                else:
                    through_data = self._ep.boolean_p2p(
                            i.data, through_data,
                            EP.ModeOr)
            info('    through_data = {}'.format(through_data))

        # determine the "on" material by joining the data of all "on" specs
        # on_data is a list of polygons from all `on` MaterialData
        # Finally we get an on_data, which is a list of Polygons
        if on:
            on_data = []
            for i in on:
                if len(on_data) == 0:
                    on_data = i.data
                else:
                    on_data = self._ep.boolean_p2p(i.data, on_data,
                                                   EP.ModeOr)
            info('    on_data = {}'.format(on_data))

        offset = self._delta
        d = self._polygons  # list of Polygon
        info('    initial d = {}'.format(d))

        if abs(buried or 0.0) > 1e-6:
            t = Trans(Point(0, -int_floor(buried / self._xs.dbu + 0.5)))
            d = [p.transformed(t) for p in d]

        # Calculate an overlap between d and into / through / on
        # in the "into" case determine the interface region between
        # self and into
        if into or through or on:
            # apply an artificial sizing to create an overlap before
            if offset == 0:
                offset = self._xs.delta_dbu / 2
                d = self._ep.size_p2p(d, 0, offset)

            if on:
                d = self._ep.boolean_p2p(d, on_data, EP.ModeAnd)
            elif through:
                d = self._ep.boolean_p2p(d, through_data, EP.ModeAnd)
            else:
                d = self._ep.boolean_p2p(d, into_data, EP.ModeAnd)

        info('    overlap d = {}'.format(d))

        pi = int_floor(prebias / self._xs.dbu + 0.5)
        info('    pi = {}'.format(pi))
        if pi < 0:
            d = self._ep.size_p2p(d, -pi, 0)
        elif pi > 0:
            # apply a positive prebias by filtering with a sized box
            dd = []
            for p in d:  # for each polygon
                box = p.bbox()  # polygon box
                if box.width() > 2 * pi:  # width
                    box = Box(box.left + pi, box.bottom,
                              box.right - pi, box.top)

                    for pp in self._ep.boolean_p2p([Polygon(box)], [p],
                                                   EP.ModeAnd):
                        dd.append(pp)
            d = dd

        xyi = int_floor(xy / self._xs.dbu + 0.5)
        zi = int_floor(z / self._xs.dbu + 0.5) - offset
        info('    xyi = {}, zi = {}'.format(xyi, zi))

        # Apply taper
        if taper:
            d = self._ep.size_p2p(d, xyi, zi, 0)
        elif xyi <= 0:
            info('    before sizing: d = {}'.format(d))
            d = self._ep.size_p2p(d, 0, zi)
            info('    after sizing: d = {}'.format(d))
        elif mode == 'round':
            # emulate "rounding" of corners by performing soft-edged sizes
            d = self._ep.size_p2p(d, xyi / 3, zi / 3, 1)
            d = self._ep.size_p2p(d, xyi / 3, zi / 3, 0)
            d = self._ep.size_p2p(d, xyi - 2 * (xyi / 3), zi - 2 * (zi / 3), 0)
        elif mode == 'square':
            d = self._ep.size_p2p(d, xyi, zi)
        elif mode == 'octagon':
            d = self._ep.size_p2p(d, xyi, zi, 1)

        if through:
            d = self._ep.boolean_p2p(d, through_data, EP.ModeANotB)

        d = self._ep.boolean_p2p(d, into_data, EP.ModeAnd)
        info('    final d = {}'.format(d))

        if None:
            # remove small features
            # Hint: this is done separately in x and y direction since that is
            # more robust against snapping distortions
            d = self._ep.size_p2p(d, 0, self._xs.delta_dbu / 2)
            d = self._ep.size_p2p(d, 0, -self._xs.delta_dbu)
            d = self._ep.size_p2p(d, 0, self._xs.delta_dbu / 2)
            d = self._ep.size_p2p(d, self._xs.delta_dbu / 2, 0)
            d = self._ep.size_p2p(d, -self._xs.delta_dbu, 0)
            d = self._ep.size_p2p(d, self._xs.delta_dbu / 2, 0)

        return d
