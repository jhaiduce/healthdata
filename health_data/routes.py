def includeme(config):
    config.add_static_view('deform_static', 'deform:static/')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('period_add','/period/add')
    config.add_route('home', '/')
