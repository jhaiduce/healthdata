def includeme(config):
    config.add_static_view('deform_static', 'deform:static/')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('node_modules', 'node_modules', cache_max_age=3600)
    config.add_route('period_add','/period/add')
    config.add_route('period_edit','/period/{period_id}/edit')
    config.add_route('period_delete','/period/{period_id}/delete')
    config.add_route('period_plot','/period')
    config.add_route('period_list','/period/list')
    config.add_route('person_add','/person/add')
    config.add_route('person_edit','/person/{person_id}/edit')
    config.add_route('person_delete','/person/{person_id}/delete')
    config.add_route('person_list','/person/list')
    config.add_route('person_set_session','/person/set_session_person/{person_id}')

    config.add_route('temperature_add','/temperature/add')
    config.add_route('temperature_edit','/temperature/{temperature_id}/edit')
    config.add_route('temperature_delete','/temperature/{temperature_id}/delete')
    config.add_route('temperature_plot','/temperature')
    config.add_route('temperature_list','/temperature/list')
    config.add_route('weight_plot','/weight/plot')
    config.add_route('blood_pressure_plot','/blood_pressure/plot')

    config.add_route('symptomtype_autocomplete','/symptomtype/autocomplete')

    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('otp_setup', '/otp_setup')
