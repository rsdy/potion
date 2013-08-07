#!/usr/bin/env python

# This file is part of potion.
#
#  potion is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  potion is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with potion. If not, see <http://www.gnu.org/licenses/>.
#
# (C) 2012- by Adam Tauber, <asciimoo@gmail.com>

if __name__ == "__main__":
    from sys import path
    from os.path import realpath, dirname
    path.append(realpath(dirname(realpath(__file__))+'/../'))

from flask import request, render_template, redirect, flash
from sqlalchemy import not_
from potion.models import Item, Source, Query
from potion.common import cfg
from flask.ext.wtf import Form, TextField, Required, SubmitField
from potion.helpers import Pagination

from potion import app, db

menu_items  = (('/'                 , 'home')
              #,('/doc'              , 'documentation')
              ,('/sources'          , 'sources')
              ,('/queries'          , 'queries')
              ,('/top'              , 'top %s unarchived' % cfg.get('app', 'items_per_page'))
              ,('/all'              , 'all')
              )

class SourceForm(Form):
    #name, address, source_type, is_public=True, attributes={}
    name                    = TextField('Name'      , [Required()])
    source_type             = TextField('Type'      , [Required()])
    address                 = TextField('Address'   , [Required()])
    submit                  = SubmitField('Submit'  , [Required()])

class QueryForm(Form):
    name         = TextField('Name' , [Required()])
    query_string = TextField('Query', [Required()])
    submit       = SubmitField('Submit'  , [Required()])

def without_rubbish(f):
    c = f.data.copy()
    del c['csrf']
    del c['submit']
    return c

class ListView(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        name_p = kwargs['name_plural']
        self.path = path = '/{}'.format(name_p)

        list_rule = path
        modify_rule = '{}/<int:o_id>'.format(path)
        delete_rule = '{}/delete/<int:o_id>'.format(path)

        app.add_url_rule(list_rule, list_rule, self.list_and_new_view,
                         methods=['GET', 'POST'])

        app.add_url_rule(modify_rule, modify_rule, self.list_modify,
                         methods=['GET', 'POST'])

        app.add_url_rule(delete_rule, delete_rule, self.list_delete,
                         methods=['GET'])

    def template(self, form, **kwargs):
        return render_template('{}.html'.format(self.name_plural)
                              ,form     = form
                              ,objects  = self.model_t.query.all())

    def handle_post(self, obj, action):
        try:
            db.session.add(obj)
            db.session.commit()
        except Exception as e:
            flash('[!] Insertion error: %r' % e)
            db.session.rollback()
            return redirect(self.path)
        else:
            flash('{} "{}" {}'.format(self.name.capitalize(), obj.name, action))
            return redirect(request.referrer or '/')

    def list_and_new_view(self):
        form = self.form_t(request.form)
        if request.method == 'POST' and form.validate():
            return self.handle_post(self.model_t(**without_rubbish(form)),
                                    'added')
        return self.template(form, mode='add')

    def list_modify(self, o_id=0):
        obj=self.model_t.query.get(o_id)
        form=self.form_t(obj=obj)
        if request.method == 'POST' and form.validate():
            for k, v in without_rubbish(form).iteritems():
                setattr(obj, k, v)

            return self.handle_post(obj, 'modified')
        return self.template(form, mode='modify', menu_path=self.path)

    def list_delete(self, o_id=0):
        cb = getattr(self, 'del_callback', None)
        if cb:
            cb(o_id)
        self.model_t.query.filter(getattr(self.model_t, '{}_id'.format(self.name))==o_id).delete()
        db.session.commit()
        flash('{} removed'.format(self.name.capitalize()))
        return redirect(request.referrer or '/')

ListView(name='query', name_plural='queries', model_t=Query, form_t=QueryForm)
ListView(name='source', name_plural='sources', model_t=Source, form_t=SourceForm,
         del_callback=lambda o: Item.query.filter(Item.source_id==o).delete())

@app.context_processor
def contex():
    global menu_items, cfg, query
    return {'menu'              : menu_items
           ,'cfg'               : cfg
           ,'query'             : ''
           ,'path'              : request.path
           ,'menu_path'         : request.path
           ,'unarchived_count'  : Item.query.filter(Item.archived==False).count()
           ,'item_count'        : Item.query.count()
           }

def parse_query(q):
    return q.get('query')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html'
                          ,sources  = Source.query.all()
                          ,queries  = Query.query.all()
                          ,unreads  = Item.query.filter(Item.archived==False).count()
                          )

def get_unarchived_ids(items):
    return [item.item_id for item in items if item.archived == False]

@app.route('/doc', methods=['GET'])
def doc():
    return 'TODO'

@app.route('/top', methods=['GET'])
@app.route('/top/<int:page_num>', methods=['GET'])
def top(page_num=1):
    limit = int(cfg.get('app', 'items_per_page'))
    offset = limit*(page_num-1)
    items = Item.query.filter(Item.archived==False).order_by(Item.added).limit(limit).offset(offset).all()
    pagination = Pagination(page_num, limit, Item.query.filter(Item.archived==False).count())
    return render_template('flat.html'
                          ,items        = items
                          ,pagination   = pagination
                          ,unarchiveds  = get_unarchived_ids(items)
                          ,menu_path    = '/top' #preserve menu highlight when paging
                          )

@app.route('/all')
@app.route('/all/<int:page_num>')
def all(page_num=1):
    limit = int(cfg.get('app', 'items_per_page'))
    offset = limit*(page_num-1)
    items = Item.query.order_by(Item.added).limit(limit).offset(offset).all()
    pagination = Pagination(page_num, limit, Item.query.count())
    return render_template('flat.html'
                          ,pagination   = pagination
                          ,items        = items
                          ,unarchiveds  = get_unarchived_ids(items)
                          ,menu_path= '/all'
                          )

@app.route('/query', methods=['POST'])
def query_redirect():
    q_str = request.form.get('query')
    return redirect('/query/'+q_str)

@app.route('/query/<path:q_str>', methods=['GET'])
def do_query(q_str):
    page_num = 1
    if(q_str.find('/')):
        try:
            page_num = int(q_str.split('/')[-1])
            q_str = ''.join(q_str.split('/')[:-1])
        except:
            pass

    reverse = False
    if(q_str.startswith('!')):
        q_str = q_str[1:]
        reverse = True

    rules = q_str.split(',')
    query = db.session.query(Item).filter(Item.source_id==Source.source_id)
    for rule in rules:
        if rule.find(':') != -1:
            item, value = rule.split(':', 1)
            if item.startswith('~'):
                query = query.filter(getattr(Item, item[1:]).contains(value))
            elif item.startswith('-'):
                query = query.filter(not_(getattr(Item, item[1:]).contains(value)))
            else:
                query = query.filter(getattr(Item, item) == value)
            continue
        if rule.startswith('_'):
            query = query.filter(Source.name == rule[1:])
            continue
    count = query.count()
    limit = int(cfg.get('app', 'items_per_page'))
    offset = limit*(page_num-1)
    items = query.limit(limit).offset(offset).all()
    if reverse:
        items.reverse()

    pagination = Pagination(page_num, limit, count)
    return render_template('flat.html'
                          ,pagination   = pagination
                          ,items        = items
                          ,unarchiveds  = get_unarchived_ids(items)
                          ,menu_path    = '/query/%s' % q_str
                          )

@app.route('/archive', methods=['POST'])
@app.route('/archive/<int:id>', methods=['GET'])
def archive(id=0):
    if request.method=='POST':
        try:
            ids = map(int, request.form.get('ids', '').split(','))
        except:
            flash('Bad params')
            return redirect(request.referrer or '/')
    elif id==0:
        flash('Nothing to archive')
        return redirect(request.referrer or '/')
    else:
        ids=[id]
    db.session.query(Item).filter(Item.item_id.in_(ids)).update({Item.archived: True}, synchronize_session='fetch')
    db.session.commit()
    if id:
        return render_template('status.html', messages=['item(%s) archived' % id])
    flash('Successfully archived items: %d' % len(ids))
    return redirect(request.referrer or '/')

@app.route('/opml', methods=('GET',))
def opml():
    return render_template('opml.xml'
                           ,sources = Source.query.filter(Source.source_type=='feed').all()
                           )

@app.route('/opml/import', methods=['GET'])
def opml_import():
    url = request.args.get('url')
    if not url:
        return 'Missing url'
    import opml
    try:
        o = opml.parse(url)
    except:
        return 'Cannot parse opml file %s' % url

    def import_outline_element(o):
        for f in o:
            if hasattr(f,'xmlUrl'):
                s = Source(f.title,'feed',f.xmlUrl)
                db.session.add(s)
            else:
                import_outline_element(f)

    import_outline_element(o)
    db.session.commit()
    flash('import successed')
    return redirect(request.referrer or '/')


if __name__ == "__main__":
    app.run(debug        = cfg.get('server', 'debug')
           ,use_debugger = cfg.get('server', 'debug')
           ,port         = int(cfg.get('server', 'port'))
           )
