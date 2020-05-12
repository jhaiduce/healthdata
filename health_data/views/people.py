from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
import json

from .showtable import SqlalchemyOrmPage

from ..models.people import Person

from .header import view_with_header

class PersonForm(colander.MappingSchema):
    id=colander.SchemaNode(
        colander.Integer(),
        widget=deform.widget.HiddenWidget(),missing=None)

    name=colander.SchemaNode(
        colander.String(),missing=None)

class DeleteForm(colander.MappingSchema):
    id=colander.SchemaNode(
        colander.Integer(),
        widget=deform.widget.HiddenWidget(),missing=None)

def appstruct_to_person(dbsession,appstruct,existing_record=None):
    if existing_record:
        person=existing_record
    else:
        person=Person()

    person.name=appstruct['name']

    return person

class PersonViews(object):
    def __init__(self,request):
        self.request=request

    def delete_form(self,buttons=['delete','cancel']):
        schema=DeleteForm().bind(
            request=self.request
        )

        return deform.Form(schema,buttons=buttons)

    def person_form(self,buttons=['submit']):
        schema=PersonForm().bind(
            request=self.request
        )

        return deform.Form(schema,buttons=buttons)

    @view_config(route_name='person_add',renderer='../templates/person_addedit.jinja2')
    def person_add(self):
        form=self.person_form().render()

        dbsession=self.request.dbsession

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.person_form().validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            person=appstruct_to_person(dbsession,appstruct)
            dbsession.add(person)

            # Flush dbsession so we can get an id assignment
            dbsession.flush()

            url = self.request.route_url('person_list')
            return HTTPFound(
                url,
                content_type='application/json',
                charset='',
                text=json.dumps(
                    {'person_id':person.id}
                )
            )

        return dict(form=form,person=None)

    @view_config(route_name='person_edit',renderer='../templates/person_addedit.jinja2')
    def person_edit(self):
        dbsession=self.request.dbsession

        person_id=int(self.request.matchdict['person_id'])
        person=dbsession.query(Person).filter(Person.id==person_id).one()

        buttons=['submit','delete entry']

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.person_form(buttons=buttons).validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            person=appstruct_to_person(dbsession,appstruct,person)

            dbsession.add(person)

            url = self.request.route_url('person_list')
            return HTTPFound(url)
        elif 'delete_entry' in self.request.params:
            url=self.request.route_url('person_delete',
                                       person_id=person.id,
                                       _query=dict(referrer=self.request.url))
            return HTTPFound(url)

        form=self.person_form(
            buttons=buttons
        ).render(dict(
            id=person.id,
            name=person.name
        ))

        return dict(form=form,person=person)

    @view_config(route_name='person_delete',renderer='../templates/person_delete_confirm.jinja2')
    def person_delete(self):
        dbsession=self.request.dbsession

        person_id=int(self.request.matchdict['person_id'])
        person=dbsession.query(Person).filter(Person.id==person_id).one()

        if 'delete' in self.request.params:
            dbsession.delete(person)
            url=self.request.route_url('person_list')
            return(HTTPFound(url))
        elif 'cancel' in self.request.params:
            referrer=self.request.params.get('referrer',self.request.referrer)
            url=referrer if referrer else self.request.route_url('person_list')
            return HTTPFound(url)

        form=self.delete_form().render(dict(id=person.id))

        return dict(form=form)

    @view_with_header
    @view_config(route_name='person_list',renderer='../templates/person_list.jinja2')
    def person_list(self):
        current_page = int(self.request.params.get("page",1))
        people=self.request.dbsession.query(Person).order_by(Person.name)
        page=SqlalchemyOrmPage(people,page=current_page,items_per_page=30)
        return dict(
            people=people,page=page
        )

    @view_config(route_name='person_set_session')
    def set_session_person(self):
        person_id=int(self.request.matchdict['person_id'])
        person=self.request.dbsession.query(Person).filter(Person.id==person_id).one()

        self.request.session['person_id']=person_id

        next_url = self.request.params.get('next', self.request.referrer)
        if not next_url:
            next_url = self.request.route_url('period_plot')

        return HTTPFound(location=next_url)
