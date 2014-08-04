#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_grid_cairo_renderer.py
=======================

Provides
--------

 * GridCairoRenderer: Renders grid slice to Cairo context
 * GridCellCairoRenderer: Renders grid cell to Cairo context
 * GridCellContentCairoRenderer: Renders cell content to Cairo context
 * GridCellBackgroundCairoRenderer: Renders cell background to Cairo context
 * GridCellBorderCairoRenderer: Renders cell border to Cairo context

"""

import cairo
import wx
import wx.lib.wxcairo
import matplotlib.pyplot
import pango
import pangocairo

from src.lib.parsers import color_pack2rgb


STANDARD_ROW_HEIGHT = 20
STANDARD_COL_WIDTH = 50

X_OFFSET = 20
Y_OFFSET = 20


try:
    from src.config import config
    MAX_RESULT_LENGTH = config["max_result_length"]
except ImportError:
    MAX_RESULT_LENGTH = 100000


class GridCairoRenderer(object):
    """Renders a grid slice to a CairoSurface

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * row_tb: 2 tuple of Integer
    \tStart and stop of row range with step 1
    * col_lr: 2 tuple of Integer
    \tStart and stop of col range with step 1
    * tab_fl: 2 tuple of Integer
    \tStart and stop of tab range with step 1

    """

    def __init__(self, context, code_array, row_tb, col_rl, tab_fl):
        self.context = context
        self.code_array = code_array

        self.row_tb = row_tb
        self.col_rl = col_rl
        self.tab_fl = tab_fl

    def get_cell_rect(self, row, col, tab):
        """Returns rectangle of cell on canvas"""

        top_row = self.row_tb[0]
        left_col = self.col_rl[0]

        pos_x = X_OFFSET
        pos_y = Y_OFFSET

        for __row in xrange(top_row, row):
            __row_height = self.code_array.get_row_height(__row, tab)
            pos_y += __row_height

        for __col in xrange(left_col, col):
            __col_width = self.code_array.get_col_width(__col, tab)
            pos_x += __col_width

        height = self.code_array.get_row_height(row, tab)
        width = self.code_array.get_col_width(col, tab)

        return pos_x, pos_y, width, height

    def draw(self):
        """Draws slice to context"""

        row_start, row_stop = self.row_tb
        col_start, col_stop = self.col_rl
        tab_start, tab_stop = self.tab_fl

        for row in xrange(row_start, row_stop):
            for col in xrange(col_start, col_stop):
                for tab in xrange(tab_start, tab_stop):
                    cell_renderer = GridCellCairoRenderer(
                        self.context,
                        self.code_array,
                        (row, col, tab),  # Key
                        self.get_cell_rect(row, col, tab)  # Rect
                    )

                    cell_renderer.draw()


class GridCellCairoRenderer(object):
    """Renders a grid cell to a CairoSurface

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * key: 3 tuple of Integer
    \tKey of cell to be rendered
    * rect: 4 tuple of float
    \tx, y, width and height of cell rectangle

    """

    def __init__(self, context, code_array, key, rect):
        self.context = context
        self.code_array = code_array
        self.key = key
        self.rect = rect

    def draw(self):
        """Draws cell to context"""

        cell_background_renderer = GridCellBackgroundCairoRenderer(
            self.context,
            self.code_array,
            self.key,
            self.rect)

        cell_content_renderer = GridCellContentCairoRenderer(
            self.context,
            self.code_array,
            self.key,
            self.rect)

        cell_border_renderer = GridCellBorderCairoRenderer(
            self.context,
            self.code_array,
            self.key,
            self.rect)

        cell_background_renderer.draw()
        cell_content_renderer.draw()
        cell_border_renderer.draw()


class GridCellContentCairoRenderer(object):
    """Renders cell content to Cairo context

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * key: 3 tuple of Integer
    \tKey of cell to be rendered

    """

    def __init__(self, context, code_array, key, rect):
        self.context = context
        self.code_array = code_array
        self.key = key
        self.rect = rect

    def get_cell_content(self):
        """Returns cell content"""

        try:
            return self.code_array[self.key]

        except IndexError:
            pass

    def draw_bitmap(self, content):
        """Draws bitmap cell content to context"""

        # TODO: Does not work
        img = wx.lib.wxcairo.ImageSurfaceFromBitmap(content)
        self.context.set_source_surface(img)
        self.context.paint()

    def draw_matplotlib(self, content):
        """Draws matplotlib cell content to context"""

        pass

    def _get_text_color(self):
        """Returns text color rgb tuple of right line"""

        color = self.code_array.cell_attributes[self.key]["textcolor"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def set_font(self, pango_layout):
        """Sets the font for draw_text"""

        wx2pango_weights = {
            wx.FONTWEIGHT_BOLD: pango.WEIGHT_BOLD,
            wx.FONTWEIGHT_LIGHT: pango.WEIGHT_LIGHT,
            wx.FONTWEIGHT_NORMAL: pango.WEIGHT_NORMAL,
        }

        wx2pango_styles = {
            wx.FONTSTYLE_NORMAL: pango.STYLE_NORMAL,
            wx.FONTSTYLE_SLANT: pango.STYLE_OBLIQUE,
            wx.FONTSTYLE_ITALIC: pango.STYLE_ITALIC,
        }

        cell_attributes = self.code_array.cell_attributes[self.key]

        # Text font attributes
        textfont = cell_attributes["textfont"]
        pointsize = cell_attributes["pointsize"]
        fontweight = cell_attributes["fontweight"]
        fontstyle = cell_attributes["fontstyle"]
        underline = cell_attributes["underline"]
        strikethrough = cell_attributes["strikethrough"]

        # Text placement attributes
#        vertical_align = cell_attributes["vertical_align"]
#        justification = cell_attributes["justification"]
#        angle = cell_attributes["angle"]

        # Now construct the pango font
        font_description = pango.FontDescription(
            " ".join([textfont, str(pointsize)]))
        pango_layout.set_font_description(font_description)

        attrs = pango.AttrList()

        # Underline
        attrs.insert(pango.AttrUnderline(underline, 0, MAX_RESULT_LENGTH))

        # Weight
        weight = wx2pango_weights[fontweight]
        attrs.insert(pango.AttrWeight(weight, 0, MAX_RESULT_LENGTH))

        # Style
        style = wx2pango_styles[fontstyle]
        attrs.insert(pango.AttrStyle(style, 0, MAX_RESULT_LENGTH))

        # Strikethrough
        attrs.insert(pango.AttrStrikethrough(strikethrough, 0,
                                             MAX_RESULT_LENGTH))

        pango_layout.set_attributes(attrs)

    def draw_text(self, content):
        """Draws matplotlib cell content to context"""

        # Text color attributes
        self.context.set_source_rgb(*self._get_text_color())

        ptx = pangocairo.CairoContext(self.context)
        pango_layout = ptx.create_layout()
        self.set_font(pango_layout)
        pango_layout.set_text(unicode(content))
        ptx.update_layout(pango_layout)
        ptx.show_layout(pango_layout)

    def draw(self):
        """Draws cell content to context"""

        content = self.get_cell_content()

        pos_x, pos_y = self.rect[:2]
        self.context.translate(pos_x + 2, pos_y + 2)

        if isinstance(content, wx._gdi.Bitmap):
            # A bitmap is returned --> Draw it!
            self.draw_bitmap(content)

        elif isinstance(content, matplotlib.pyplot.Figure):
            # A matplotlib figure is returned --> Draw it!
            self.draw_matplotlib_figure(content)

        elif content is not None:
            self.draw_text(content)

        self.context.translate(-pos_x - 2, -pos_y - 2)


class GridCellBackgroundCairoRenderer(object):
    """Renders cell background to Cairo context

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * key: 3 tuple of Integer
    \tKey of cell to be rendered

    """

    def __init__(self, context, code_array, key, rect):
        self.context = context
        self.cell_attributes = code_array.cell_attributes
        self.key = key
        self.rect = rect

    def _get_background_color(self):
        """Returns background color rgb tuple of right line"""

        color = self.cell_attributes[self.key]["bgcolor"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def draw(self):
        """Draws cell background to context"""

        self.context.set_source_rgb(*self._get_background_color())
        self.context.rectangle(*self.rect)
        self.context.fill()


class GridCellBorderCairoRenderer(object):
    """Renders cell border to Cairo context

    Parameters
    ----------

    * context: pycairo.context
    \tThe Cairo context to be drawn to
    * code_array: model.code_array
    \tGrid data structure that yields rendering information
    * key: 3 tuple of Integer
    \tKey of cell to be rendered

    """

    def __init__(self, context, code_array, key, rect):
        self.context = context
        self.code_array = code_array
        self.cell_attributes = code_array.cell_attributes
        self.key = key
        self.rect = rect

    # Coordinates
    # -----------

    def _get_top_line_coordinates(self):
        """Returns start and stop coordinates of bottom line"""

        rect_x, rect_y, rect_width, _ = self.rect

        start_point = rect_x, rect_y
        end_point = rect_x + rect_width, rect_y

        return start_point, end_point

    def _get_bottom_line_coordinates(self):
        """Returns start and stop coordinates of bottom line"""

        rect_x, rect_y, rect_width, rect_height = self.rect

        start_point = rect_x, rect_y + rect_height
        end_point = rect_x + rect_width, rect_y + rect_height

        return start_point, end_point

    def _get_left_line_coordinates(self):
        """Returns start and stop coordinates of right line"""

        rect_x, rect_y, _, rect_height = self.rect

        start_point = rect_x, rect_y
        end_point = rect_x, rect_y + rect_height

        return start_point, end_point

    def _get_right_line_coordinates(self):
        """Returns start and stop coordinates of right line"""

        rect_x, rect_y, rect_width, rect_height = self.rect

        start_point = rect_x + rect_width, rect_y
        end_point = rect_x + rect_width, rect_y + rect_height

        return start_point, end_point

    def _get_topleft_right_line_coordinates(self):
        """Returns start and stop coordinates of top left cell's right line"""

        rect_x, rect_y, _, _ = self.rect

        start_point = rect_x, rect_y - 0.01
        end_point = rect_x, rect_y

        return start_point, end_point

    def _get_topleft_bottom_line_coordinates(self):
        """Returns start and stop coordinates of top left cell's bottom line"""

        rect_x, rect_y, _, _ = self.rect

        start_point = rect_x - 0.01, rect_y
        end_point = rect_x, rect_y

        return start_point, end_point

    # Colors
    # ------

    def _get_top_line_color(self):
        """Returns color rgb tuple of top line"""

        row, col, tab = self.key
        key = row - 1, col, tab
        color = self.cell_attributes[key]["bordercolor_bottom"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def _get_bottom_line_color(self):
        """Returns color rgb tuple of bottom line"""

        color = self.cell_attributes[self.key]["bordercolor_bottom"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def _get_left_line_color(self):
        """Returns color rgb tuple of left line"""

        row, col, tab = self.key
        key = row, col - 1, tab
        color = self.cell_attributes[key]["bordercolor_right"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def _get_right_line_color(self):
        """Returns color rgb tuple of right line"""

        color = self.cell_attributes[self.key]["bordercolor_right"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def _get_topleft_right_line_color(self):
        """Returns color rgb tuple of right line of top left cell"""

        row, col, tab = self.key
        key = row - 1, col - 1, tab
        color = self.cell_attributes[key]["bordercolor_right"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    def _get_topleft_bottom_line_color(self):
        """Returns color rgb tuple of bottom line of top left cell"""

        row, col, tab = self.key
        key = row - 1, col - 1, tab
        color = self.cell_attributes[key]["bordercolor_bottom"]
        return tuple(c / 255.0 for c in color_pack2rgb(color))

    # Widths
    # ------

    def _get_top_line_width(self):
        """Returns width of top line"""

        row, col, tab = self.key
        key = row - 1, col, tab
        return float(self.cell_attributes[key]["borderwidth_bottom"]) / 2.0

    def _get_bottom_line_width(self):
        """Returns width of bottom line"""

        return float(self.cell_attributes[self.key]["borderwidth_bottom"]) / 2.

    def _get_left_line_width(self):
        """Returns width of left line"""

        row, col, tab = self.key
        key = row, col - 1, tab
        return float(self.cell_attributes[key]["borderwidth_right"]) / 2.0

    def _get_right_line_width(self):
        """Returns width of right line"""

        return float(self.cell_attributes[self.key]["borderwidth_right"]) / 2.0

    def _get_topleft_right_line_width(self):
        """Returns width of right line of top left cell"""

        row, col, tab = self.key
        key = row - 1, col - 1, tab
        return float(self.cell_attributes[key]["borderwidth_right"]) / 2.0

    def _get_topleft_bottom_line_width(self):
        """Returns width of bottom line of top left cell"""

        row, col, tab = self.key
        key = row - 1, col - 1, tab
        return float(self.cell_attributes[key]["borderwidth_bottom"]) / 2.0

    # Drawing
    # -------

    def _draw_line(self, start_point, end_point):
        """Draws a line without setting color or width

        Parameters
        ----------
        start_point: 2 tuple of Integer
        \tStart point of line
        end_point
        \tEnd point of line

        """

        self.context.move_to(*start_point)
        self.context.line_to(*end_point)
        self.context.stroke()

    def _draw_left_line(self):
        """Draws left line setting color and width"""

        self.context.set_source_rgb(*self._get_left_line_color())
        self.context.set_line_width(self._get_left_line_width())
        self._draw_line(*self._get_left_line_coordinates())

    def _draw_right_line(self):
        """Draws right line setting color and width"""

        self.context.set_source_rgb(*self._get_right_line_color())
        self.context.set_line_width(self._get_right_line_width())
        self._draw_line(*self._get_right_line_coordinates())

    def _draw_top_line(self):
        """Draws top line setting color and width"""

        self.context.set_source_rgb(*self._get_top_line_color())
        self.context.set_line_width(self._get_top_line_width())
        self._draw_line(*self._get_top_line_coordinates())

    def _draw_bottom_line(self):
        """Draws bottom line setting color and width"""

        self.context.set_source_rgb(*self._get_bottom_line_color())
        self.context.set_line_width(self._get_bottom_line_width())
        self._draw_line(*self._get_bottom_line_coordinates())

    def _draw_tlr_line(self):
        """Draws bottom line setting color and width"""

        self.context.set_source_rgb(*self._get_topleft_right_line_color())
        self.context.set_line_width(self._get_topleft_right_line_width())
        self._draw_line(*self._get_topleft_right_line_coordinates())

    def _draw_tlb_line(self):
        """Draws bottom line setting color and width"""

        self.context.set_source_rgb(*self._get_topleft_bottom_line_color())
        self.context.set_line_width(self._get_topleft_bottom_line_width())
        self._draw_line(*self._get_topleft_bottom_line_coordinates())

    def draw(self):
        """Draws cell border to context"""

        # Lines should have a square cap to avoid ugly edges
        self.context.set_line_cap(cairo.LINE_CAP_SQUARE)

        # Sort lines from thinnest to thickest
        width_func = [
            (self._get_left_line_width(),
             -sum(self._get_left_line_color()), self._draw_left_line),
            (self._get_right_line_width(),
             -sum(self._get_right_line_color()), self._draw_right_line),
            (self._get_top_line_width(),
             -sum(self._get_top_line_color()), self._draw_top_line),
            (self._get_bottom_line_width(),
             -sum(self._get_bottom_line_color()), self._draw_bottom_line),
            (self._get_topleft_right_line_width(),
             -sum(self._get_topleft_right_line_color()), self._draw_tlr_line),
            (self._get_topleft_bottom_line_width(),
             -sum(self._get_topleft_bottom_line_color()), self._draw_tlb_line),
        ]

        width_func.sort()

        for _, _, draw_func in width_func:
            draw_func()