import os
from pathlib import Path
import zipfile
import re
import uuid
import base64

import numpy as np
import pandas as pd
import xarray

import bokeh
from bokeh.io import show
from bokeh.layouts import layout, column, row, Spacer
from bokeh.models import ColumnDataSource
from bokeh.models import Select, Button, Div, Slider
from bokeh.models.tools import HoverTool, CrosshairTool
from bokeh.plotting import figure, curdoc
from bokeh.models.widgets import CheckboxGroup
from bokeh.themes import Theme, built_in_themes
#
from itsdangerous import TimestampSigner
# rom itsdangerous import BadSignature, SignatureExpired

import sys
sys.path.append("fontawesome")
from fontawesome.fontawesome_icon import FontAwesomeIcon

from nc_transform import get_plottable_variables, get_nc_data, get_tsp_data_dict

curdoc_element = curdoc()
args = curdoc_element.session_context.request.arguments


if not Path(os.environ['TSPLOT_DOWNLOAD']).exists():
    Path(os.environ['TSPLOT_DOWNLOAD']).mkdir(parents=True, exist_ok=True)

def get_variables(resource_url):
    plottable_variables = get_plottable_variables(resource_url)
    return plottable_variables

class metadict(dict):
    pass

def get_data(resource_url):
    variables_dict = get_plottable_variables(resource_url)
    variables = list(list(variables_dict.values())[0])
    axis = list(variables_dict.keys())[0]
    data = get_nc_data(resource_url)
    dataset_metadata = data.dataset_metadata
    variable_metadata = data.variable_metadata
    data = data[variables]
    if axis == 'y_axis':
        data.dataset_metada = ''
        data.dataset_metada = dataset_metadata
        data.variable_metadata = ''
        data.variable_metadata = variable_metadata
        data.feature_type = ''
        data.feature_type = 'TimeSeries'
        return data
    if axis == 'x_axis':
        if len(data.index.names) == 2:
            tsp = get_tsp_data_dict(data)
            tsp = metadict(tsp)
            tsp.dataset_metadata = ''
            tsp.dataset_metadata = dataset_metadata
            tsp.variable_metadata = ''
            tsp.variable_metadata = variable_metadata
            tsp.feature_type = ''
            tsp.feature_type = 'TimeSeriesProfile'
            return tsp
        else:
            data.dataset_metada = ''
            data.dataset_metada = dataset_metadata
            data.variable_metadata = ''
            data.variable_metadata = variable_metadata
            data.feature_type = ''
            data.feature_type = 'Profile'
            return data
        
def show_hide_theme(event):
    if theme_select.visible:
        theme_select.visible = False
        fontsize_adjustments.visible = False
    else:
        theme_select.visible = True
        fontsize_adjustments.visible = True

def show_hide_export(event):
    if export_layout.visible:
        export_layout.visible = False
    else:
        export_layout.visible = True

def data_download(event):
    download_url.text=''
    output_format = 'csv'
    rv = base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
    unique = re.sub(r'[\=\+\/]', lambda m: {'+': '-', '/': '_', '=': ''}[m.group(0)], rv)
    filename = str(unique) + '.' + str(output_format)
    s = TimestampSigner('secret-key')
    download_token = s.sign(filename).decode()
    # dirpath = os.path.join(os.path.dirname(__file__),'static', download)
    dirpath = os.environ['TSPLOT_DOWNLOAD']
    outfile = Path(dirpath, str(download_token))
    if data.feature_type == 'TimeSeriesProfile':
        index_range = np.array([p.y_range.end, p.y_range.start]).tolist()
    else:
        index_range = np.array([p.x_range.start, p.x_range.end], dtype='i8').view('datetime64[ms]').tolist()
    start = df.index.searchsorted(index_range[0])
    end = df.index.searchsorted(index_range[1])
    # TODO: check for the output format [netcdf / csv]
    if export_format.value=='csv':
        compression_opts = dict(method='zip', archive_name=f'{select.value}.csv')
        #df[select.value][df.index[start]:df.index[end-1]].to_csv(outfile, header=True)
        #
        ### df[select.value][df.index[start]:df.index[end-1]].to_csv(outfile, compression=compression_opts, header=True)
        df[[variables[x] for x in export_variables.active]][df.index[start]:df.index[end-1]].to_csv(outfile, 
                                                                                                    compression=compression_opts, 
                                                                                                    header=True)
        # zip_resource = zipfile.ZipFile(outfile, 'a')
        # shall we add a figure?
        # zip.write('metadata.html', os.path.basename('metadata.html'))
        # zip_resource.close()
    else: 
        xr = xarray.Dataset.from_dataframe(df[[variables[x] for x in export_variables.active]][df.index[start]:df.index[end-1]]) 
        # TODO: add attributes and metadata, probably worth to do some reindexing
        xr.to_netcdf(outfile)                                                                                          
    #
    # url_text=f'<a href="http://localhost:5100/test/TS-Plot/static/Download/{download_token}">Variable: {select.value}, from: {df.index[start]} to: {df.index[end-1]}</a>'
    try:
        server_domain = os.environ['ORIGIN']
        prefix = os.environ['PREFIX']
    except KeyError:
        server_domain = 'localhost:5100'
        prefix = 'test'
    url_text=f'<a href="http://{server_domain}/{prefix}/TS-Plot/static/Download/{download_token}">Direct download for the selected variables, from: {df.index[start]} to: {df.index[end-1]}</a>'
    if data.feature_type == 'TimeSeriesProfile':
        date_time = get_datetime_string(list(data.keys())[int(slider.value)])
        url_text += f' selected profile: # {slider.value} {date_time}'  
    download_url.text=url_text

def resampler(attr, old, new):
    if new == 0:
        data = df
    else:
        data = df.resample(new).mean().interpolate(method='linear').copy()
        data['tooltip'] = [x.strftime("%Y-%m-%d") for x in data.index]
    ds.data = data

def get_datetime_string(datetime):
    date = datetime.split(' ')[0]
    time = datetime.split(' ')[1]
    return f"<ul style='text-align:left;'><li>Date: <b>{date}</b></li><li>Time: <b>{time}</b></li></ul>"

def tsp_handler(value, old, new):
    df = data[list(data.keys())[int(slider.value)]] # .to_frame()
    ds.data = df

    xlabel = new #get_y_label(new)
    var_label = '@{' + str(new + '}')

    tooltips = [(df.index.name, '@'+df.index.name),
            (xlabel, var_label)
            ]
    hover.tooltips = tooltips
    #
    p.xaxis.axis_label = xlabel

    '''
    y = [df[new].dropna().index.min(), df[new].dropna().index.max()]
    x = [df[new].dropna().min(), df[new].dropna().max()]

    p.y_range.start = y[1] 
    p.y_range.end = y[0] 
    p.x_range.start = x[0] 
    p.x_range.end = x[1] 
    '''
    share_x = True
    if share_x:
        y = np.array([p.y_range.start, p.y_range.end]).tolist()
        start = df.index.searchsorted(y[1])
        end = df.index.searchsorted(y[0])
        try:
            p.x_range.start = df.iloc[start:end][new].min()
            p.x_range.end = df.iloc[start:end][new].max()
        except ValueError:
            p.x_range.start = df[new].min()
            p.x_range.end = df[new].max()


    line_renderer.glyph.x = dict(field=new)
    circle_renderer.glyph.x = dict(field=new)

def time_slider_handler(value, old, new):
    df = data[list(data.keys())[int(new)]] # .to_frame()
    ds.data = df

    y = [df[select.value].dropna().index.min(), df[select.value].dropna().index.max()]
    x = [df[select.value].dropna().min(), df[select.value].dropna().max()]
    

    p.y_range.start = y[1] 
    p.y_range.end = y[0] 
    p.x_range.start = x[0] 
    p.x_range.end = x[1] 
    
    # line_renderer.glyph.x = dict(field=select.value)
    # circle_renderer.glyph.x = dict(field=select.value)
    list(data.keys())[int(new)]
    par.text = get_datetime_string(list(data.keys())[int(new)])

def left_btn_handler(event):
    if slider.value > slider.start:
        slider.value = slider.value -1

def right_btn_handler(event):
    if slider.value <= slider.end - 1:
        slider.value = slider.value + 1

def ts_handler(value, old, new):
    line_renderer.glyph.y = dict(field=new)
    circle_renderer.glyph.y = dict(field=new)

    ylabel = get_y_label(new)
    var_label = '@{' + str(new + '}')
    tooltips = [('Time', '@tooltip'),
            (ylabel, var_label)
            ]
    hover.tooltips = tooltips
    p.yaxis.axis_label = ylabel
    
    x = np.array([p.x_range.start, p.x_range.end], dtype='i8').view('datetime64[ms]').tolist()
    start = df.index.searchsorted(x[0])
    end = df.index.searchsorted(x[1])
    try:
        p.y_range.start = df.iloc[start:end][new].min()
        p.y_range.end = df.iloc[start:end][new].max()
    except ValueError:
        p.y_range.start = df[new].min()
        p.y_range.end = df[new].max()

def p_handler(value, old, new):
    line_renderer.glyph.x = dict(field=new)
    circle_renderer.glyph.x = dict(field=new)

    xlabel = new #get_y_label(new)
    var_label = '@{' + str(new + '}')

    tooltips = [(df.index.name, '@'+df.index.name),
            (xlabel, var_label)
            ]
    hover.tooltips = tooltips
    #
    p.xaxis.axis_label = xlabel
    line_renderer.glyph.x = dict(field=new)
    circle_renderer.glyph.x = dict(field=new)

    share_x = True
    if share_x:
        y = np.array([p.y_range.start, p.y_range.end]).tolist()
        start = df.index.searchsorted(y[1])
        end = df.index.searchsorted(y[0])
        try:
            p.x_range.start = df.iloc[start:end][new].min()
            p.x_range.end = df.iloc[start:end][new].max()
        except ValueError:
            p.x_range.start = df[new].min()
            p.x_range.end = df[new].max()


def get_y_label(selected_variable):
    try:
        var_tooltip_label = str(df.variable_metadata[selected_variable]['long_name'])
    except KeyError:
        var_tooltip_label = str(df.variable_metadata[selected_variable]['standard_name'])
    try:
        units = list({'unit', 'units'}.intersection(df.variable_metadata[selected_variable]))[0]
        y_axis_label = " ".join(
            [var_tooltip_label, '[', df.variable_metadata[selected_variable][units], ']'])
    except IndexError:
        print('no units found')
        y_axis_label = var_tooltip_label
    var_label = '@{' + str(selected_variable + '}')
    tooltips = [('Time', '@tooltip'),
            (var_tooltip_label, var_label)
            ]
    return y_axis_label

def switch_theme(value, old, new):
    if new in ['dark_minimal', 'night_sky', 'contrast']:
        for i in p.toolbar.tools:
            if type(i) == type(CrosshairTool()):
                p.toolbar.tools.remove(i)
                p.add_tools(CrosshairTool(line_color='white'))
    else:
        for i in p.toolbar.tools:
            if type(i) == type(CrosshairTool()):
                p.toolbar.tools.remove(i)
                p.add_tools(CrosshairTool(line_color='black'))
    curdoc().theme = new

    '''
    curdoc().theme = Theme(json={'attrs' : {
        'Figure' : {
            'background_fill_color': '#2F2F2F',
            'border_fill_color': '#2F2F2F',
            'outline_line_color': '#444444',
            },
        'Axis': {
            'axis_line_color': 'aqua',
            },
        'Grid': {
            'grid_line_dash': [6, 4],
            'grid_line_alpha': 0.3,
            },
        'Title': {
            'text_color': 'white'
            }
        }})
    '''
    # curdoc().theme = Theme(filename=os.path.join(os.path.dirname(__file__),'static', 'themes', 'test_theme.yaml'))

def increase_font(event):
    y = [p.y_range.start, p.y_range.end]
    x = [p.x_range.start, p.x_range.end]
    # border = [p.min_border_left, p.min_border_right]
    major_label_text_font_size = int(p.xaxis.major_label_text_font_size.replace('pt',''))
    axis_label_text_font_size = int(p.xaxis.axis_label_text_font_size.replace('pt',''))
    p.xaxis.major_label_text_font_size= str(major_label_text_font_size+1)+'pt'
    p.yaxis.major_label_text_font_size= str(major_label_text_font_size+1)+'pt'
    p.yaxis.axis_label_text_font_size = str(axis_label_text_font_size+1)+'pt'
    p.xaxis.axis_label_text_font_size = str(axis_label_text_font_size+1)+'pt'
    p.y_range.start, p.y_range.end = y
    p.x_range.start, p.x_range.end = x 
    # p.min_border_left = border[0]+10
    # p.min_border_right = border[0]+10

def decrease_font(event):
    y = [p.y_range.start, p.y_range.end]
    x = [p.x_range.start, p.x_range.end]
    # border = [p.min_border_left, p.min_border_right]
    major_label_text_font_size = int(p.xaxis.major_label_text_font_size.replace('pt',''))
    axis_label_text_font_size = int(p.xaxis.axis_label_text_font_size.replace('pt',''))
    p.xaxis.major_label_text_font_size= str(major_label_text_font_size-1)+'pt'
    p.yaxis.major_label_text_font_size= str(major_label_text_font_size-1)+'pt'
    p.yaxis.axis_label_text_font_size = str(axis_label_text_font_size-1)+'pt'
    p.xaxis.axis_label_text_font_size = str(axis_label_text_font_size-1)+'pt'
    p.y_range.start, p.y_range.end = y
    p.x_range.start, p.x_range.end = x
    # p.min_border_left = border[0]-10
    # p.min_border_right = border[0]-10

def get_labels(obj, variable):
    try:
        var_tooltip_label = str(obj.variable_metadata[variable]['long_name'])
    except KeyError:
        var_tooltip_label = str(obj.variable_metadata[variable]['standard_name'])
    try:
        units = list({'unit', 'units'}.intersection(obj.variable_metadata[variable]))[0]
        y_axis_label = " ".join(
            [var_tooltip_label, '[', obj.variable_metadata[variable][units], ']'])
    except IndexError:
        print('no units found')
        y_axis_label = var_tooltip_label
    var_label = '@{' + str(variable + '}')
    return [var_label, var_tooltip_label, y_axis_label]


nc_url = str(args.get('url')[0].decode())
data = get_data(nc_url)

if data.feature_type == 'TimeSeriesProfile':
    preselected_variable = data[list(data.keys())[0]].columns[0]
    df = data[list(data.keys())[0]] # [preselected_variable].to_frame()
    variables = list(df.columns)
    df.dataset_metadata = ''
    df.dataset_metadata = data.dataset_metadata
    df.variable_metadata = ''
    df.variable_metadata = data.variable_metadata
    var_label, var_tooltip_label, x_axis_label = get_labels(df, preselected_variable)
    tooltips = [('Index', '@'+ df.index.name),
        (var_tooltip_label, var_label)
        ]
    x_axis_type="linear"
    y_axis_label=df.index.name
    hover_formatter = "numeral"
    y, x = df.index.name, variables[0]
    y_range_flipped = True
    handler = tsp_handler
    # Div
    html_text = get_datetime_string(list(data.keys())[0])
    par = Div(text=html_text)

    # Buttons
    left_btn = Button(icon=FontAwesomeIcon(icon_name="chevron-left", size=1), height=40,  width=40, label='')
    right_btn = Button(icon=FontAwesomeIcon(icon_name="chevron-right", size=1), height=40,  width=40, label='')
    # Spacer
    sp = Spacer(width=50)
    # Slider Labels
    # end_label = Div(text=list(data.keys())[-1])
    # start_label = Div(text=list(data.keys())[0])
    # end_label = Div(text=list(data.keys())[-1].split(' ')[0] + \
    #                     '<br>' \
    #                     + list(data.keys())[-1].split(' ')[1],
    #                style={'text-align': 'right'})
    # start_label = Div(text=list(data.keys())[0].split(' ')[0] + \
    #                       '<br>' \
    #                       + list(data.keys())[0].split(' ')[1],
    #                  style={'text-align': 'left'})

    slider = Slider(title="Profile # ",
                        value=0,
                        start=0,
                        end=len(data.keys()) - 1,
                        step=1,
                        show_value=True,
                        tooltips=False,
                        bar_color='darkslategray') 
    slider.on_change('value', time_slider_handler)
    widget_to_show = ''

    left_btn.on_click(left_btn_handler)
    right_btn.on_click(right_btn_handler)

    slider_wrapper = layout([
            [Spacer(width=100), slider, left_btn, right_btn, par],
        ])
            # [Spacer(width=100), start_label, Spacer(width=150), end_label, Spacer(width=100)],
if data.feature_type == 'TimeSeries':
    df = data
    variables = list(data.columns)
    df['tooltip'] = [x.strftime("%Y-%m-%d %H:%M:%S") for x in df.index]
    var_label, var_tooltip_label, y_axis_label = get_labels(df, variables[0])
    tooltips = [('Time', '@tooltip'),
            (var_tooltip_label, var_label)
            ]
    x_axis_type="datetime"
    x_axis_label='Date-Time'
    hover_formatter = "datetime"
    x, y = df.index.name, variables[0]
    y_range_flipped = False
    handler = ts_handler
if data.feature_type == 'Profile':
    df = data
    variables = list(data.columns)
    var_label, var_tooltip_label, x_axis_label = get_labels(df, variables[0])
    tooltips = [('Index', '@'+ df.index.name),
        (var_tooltip_label, var_label)
        ]
    x_axis_type="linear"
    y_axis_label=df.index.name
    hover_formatter = "numeral"
    y, x = df.index.name, variables[0]
    y_range_flipped = True
    handler = p_handler

tools_to_show = "box_zoom, pan, save, hover, reset, wheel_zoom, crosshair"
ds = ColumnDataSource(df)

p = figure(toolbar_location="above", 
            tools=tools_to_show,
            x_axis_type=x_axis_type,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label)
p.toolbar.logo = None
p.sizing_mode = 'stretch_width'

hover = p.select(dict(type=HoverTool))
hover.formatters = {'tooltip': hover_formatter}
hover.tooltips = tooltips

line_renderer = p.line( x=x, 
                        y=y, 
                        source=ds, 
                        ) 

circle_renderer = p.circle(x=x,
                           y=y,
                           source=ds,
                           size=3,
                           fill_alpha=0.5,
                           fill_color='white',
                           legend_label='Data-Points',
                           )
circle_renderer.visible = False

p.y_range.flipped = y_range_flipped
p.min_border_left = 80
p.min_border_right = 80
# p.background_fill_color = "SeaShell"
# p.background_fill_alpha = 0.5
p.legend.location = "top_left"
p.legend.click_policy = "hide"
# TODO: Add widget to increase/decrease the font size
p.xaxis.major_label_text_font_size='10pt'
p.yaxis.major_label_text_font_size='10pt'
p.yaxis.axis_label_text_font_size = "16pt"
p.xaxis.axis_label_text_font_size = "16pt"
p.xaxis.major_label_orientation = np.pi/4

select = Select(title="Select variable:", 
                value=variables[0], 
                options=variables, 
                css_classes=['custom_select'])
select.on_change('value', handler)

resampling = Select(title="Frequency:", 
                    options=['H', 'D', 'W','M', 'Q', 'Y'], 
                    css_classes=['custom_select'])
resampling.on_change('value', resampler)

download = Button(label="Data Export", 
                button_type="primary", 
                height=40, 
                width=120) # , width_policy='fixed'
download.on_click(show_hide_export)

accessibility = Button(icon=FontAwesomeIcon(icon_name="low-vision", size=2), 
                        height=50,  
                        width=50, 
                        label='')
accessibility.on_click(show_hide_theme)

download_url = Div(text=""" """, width_policy='fixed') 

theme_select = Select(title='Theme', options=['dark_minimal', 
                                              'light_minimal', 
                                              'night_sky', 
                                              'contrast'], 
                                    value = 'light_minimal',
                                    css_classes=['custom_select'])
theme_select.on_change('value', switch_theme)
theme_select.visible = False

increase_fontsize = Button(icon=FontAwesomeIcon(icon_name="plus", size=1), 
                        height=30, 
                        width=30, 
                        label='')
decrease_fontsize = Button(icon=FontAwesomeIcon(icon_name="minus", size=1), 
                        height=30, 
                        width=30, 
                        label='')
increase_fontsize.on_click(increase_font) 
decrease_fontsize.on_click(decrease_font) 

fontsize_label = Div(text='<font size = "2" color = "darkslategray" ><b>Fontsize<b></font>')
fontsize_adjustments = column(fontsize_label, 
                            Spacer(width=10, height=10), 
                            row(decrease_fontsize, Spacer(width=5, height=30), increase_fontsize))
fontsize_adjustments.visible = False

# create the export widget-box
# format:
export_format =  Select(title="Select output data format:", 
                        value='csv', 
                        options=['csv', 'NetCDF'], 
                        css_classes=['custom_select'])

export_variables = CheckboxGroup(labels=variables, 
                                css_classes=['custom_select'])

export_button = Button(icon=FontAwesomeIcon(icon_name="download", size=2), 
                        height=40, 
                        width=30, 
                        label='')
export_button.on_click(data_download)

export_layout = layout([[row(export_button, 
                            Spacer(width=60, height=60), 
                            download_url)], 
                        [row([export_format, 
                            Spacer(width=60, height=60), 
                            column(Div(text='<font size = "2" color = "darkslategray" ><b>Select Variables to export:<b></font>', 
                                        css_classes=['widget_label'], 
                                        height=20), 
                                    export_variables, 
                            sizing_mode='fixed')])]], 
                        sizing_mode='fixed')

export_layout.visible = False
curdoc_element.title = "TS-Plot"

if data.feature_type == 'TimeSeriesProfile':
    curdoc_element.add_root(column(row(select, 
                                       slider_wrapper,
                                       Spacer(width=100, height=10, sizing_mode='scale_width'), 
                                       row(theme_select, fontsize_adjustments, Spacer(width=20, height=30), accessibility)), 
                                    p, 
                                    row(download, 
                                    export_layout),
                                sizing_mode='scale_width'))
else:
    curdoc_element.add_root(column(row(select, 
                                        resampling, 
                                        Spacer(width=100, height=10, sizing_mode='scale_width'), 
                                        row(theme_select, fontsize_adjustments, Spacer(width=20, height=30), accessibility)), 
                                    p, 
                                    row(download,
                                    export_layout), 
                                sizing_mode='scale_width'))
