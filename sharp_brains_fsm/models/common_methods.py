import xlwt
from openerp.exceptions import ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api,exceptions, _
from collections import Counter
import base64
from xlutils.copy import copy
from io import StringIO

from xlwt import easyxf

try:
    import xlwt
except ImportError:
    xlwt = None

try:
    import xlrd
    from xlrd import *
except ImportError:
    xlrd = None
import logging
_logger = logging.getLogger(__name__)

hide = True
style5 = xlwt.XFStyle()
style0 = xlwt.easyxf("font: name 'Century Gothic', bold on, height 200; align:wrap 0")
gray = xlwt.Style.colour_map['gray_ega']
color1 = 'gray25'
color1 = xlwt.Style.colour_map[color1]
red = xlwt.Style.colour_map['red']
style1 = xlwt.easyxf("font: name 'Verdana', bold on, colour_index "+str(gray)+"; align: horiz center,wrap 1")
style2 = xlwt.easyxf("font: name 'Century Gothic'; align:wrap 0")
style3 = xlwt.easyxf("protection: cell_locked false; border: top_color red, bottom_color red, right_color red, left_color red,\
                          left thin, right thin, top thin, bottom thin;\
                 pattern: pattern solid, fore_color white;")
style4 = xlwt.easyxf("font: name 'Verdana', bold on, colour_index "+str(red)+"; align: horiz center")
style4.alignment.wrap = 1
style5 = xlwt.easyxf("font: name 'Verdana', colour_index "+str(red)+";")

styleTitle = xlwt.easyxf("font: name 'Century Gothic', bold on, height 250 ; align:wrap 1, horiz center, vert center")
styleValue = xlwt.easyxf("font: name 'Century Gothic', bold on, height 250 ; align:wrap 1, horiz center, vert center")

style6 = xlwt.easyxf("border: top_color red, bottom_color red, right_color red, left_color red,\
                          left thin, right thin, top thin, bottom thin;\
                 pattern: pattern solid, fore_color "+str(color1)+";")


styleLegend = xlwt.easyxf("font: name 'Century Gothic', bold on, height 250 ; align:wrap 1, horiz center, vert center;pattern: pattern solid, fore_colour gray25;")

style5.alignment.wrap = 1
style_for_date = xlwt.XFStyle()
style_for_date.num_format_str='YYYY-MM-DD'

style_for_number= xlwt.XFStyle()
style_for_number.num_format_str='0000000000000'

style_for_str= xlwt.XFStyle()
style_for_str.num_format_str='@'
row = 0 # min row value must be 0
col = 2 # min column value will b 2
col_width=10
col_width_1=15
col_width_2=35
# read_only = xlwt.easyxf("protection: cell_locked true;")

def prepare_worksheet(self,sheet_name,title,tot_col,tot_legend=None):
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet(sheet_name)
    worksheet.panes_frozen = True
    # worksheet.protect = True
    worksheet.horz_split_pos = 2
    worksheet.vert_split_pos = 2

    worksheet.col(0).hidden = hide
    worksheet.col(1).hidden = hide
    worksheet.row(1).hidden= hide

    worksheet.write_merge(row, row, col , col ,'Title', styleTitle)
    worksheet.row(row).height_mismatch = True
    worksheet.row(row).height = 256 * 6

    worksheet.write_merge(row, row, col+1 , col+tot_col-1 ,title, styleValue)

    if tot_legend:
        tot_legend = ((tot_legend * 2) - 1) + (tot_col + col)
        worksheet.write_merge(row, row, tot_col + col + 1, tot_legend + 1, "Legend", styleLegend)
     
    return workbook,worksheet


