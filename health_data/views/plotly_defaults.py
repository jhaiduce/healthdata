default_axis_style={
    "backgroundcolor": "#E5ECF6",
    "gridcolor": "white",
    "gridwidth": 2,
    "linecolor": "white",
    "showbackground": True,
    "ticks": "",
    "zerolinecolor": "white"
}

def get_axis_range(data,start_idx=0,end_idx=-1,pad_scale=0.06):

    start_idx=min(max(start_idx,-len(data)),len(data)-1)
    end_idx=min(max(end_idx,-len(data)),len(data)-1)

    xmin=data.iloc[start_idx]
    xmax=data.iloc[end_idx]

    xmin=xmin-pad_scale*(xmax-xmin)
    xmax=xmax+pad_scale*(xmax-xmin)

    return xmin, xmax
