# Copyright (C) 2009, Mathieu PASQUET <kiorky@cryptelium.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the <ORGANIZATION> nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__docformat__ = 'restructuredtext en'

import os
import shutil
import re
import urllib2

import pkg_resources

from iniparse import ConfigParser

from minitage.paste.projects import common
from minitage.paste.common import var
from minitage.core.common  import search_latest

class NoDefaultTemplateError(Exception): pass

default_config = pkg_resources.resource_filename('minitage.paste', 'projects/plone3/minitage.plone3.xml')
user_config = os.path.join( os.path.expanduser('~'), '.minitage.plone3.xml')
vars = common.read_vars(default_config, user_config)
# plone quickinstaller option/names mappings
qi_mappings = vars.get('qi_mappings', {})
# eggs registered as Zope2 packages
z2packages = vars.get('z2packages', {})
z2products = vars.get('z2products', {})
# variables discovered via configuration
addons_vars = vars.get('addons_vars', [])
# mappings option/eggs to install
eggs_mappings = vars.get('eggs_mappings', {})
# scripts to generate
scripts_mappings = vars.get('scripts_mappings', {})
# mappings option/zcml to install
zcml_loading_order = vars.get('zcml_loading_order', {})
zcml_mappings = vars.get('zcml_mappings', {})
# mappings option/versions to pin
versions_mappings = vars.get('versions_mappings', {})
# mappings option/versions to pin if the user wants really stable sets
checked_versions_mappings = vars.get('checked_versions_mappings',{})
# mappings option/productdistros to install
urls_mappings = vars.get('urls_mappings', {})
# mappings option/nested packages/version suffix packages  to install
plone_np_mappings = vars.get('plone_np_mappings', {})
plone_vsp_mappings = vars.get('plone_vsp_mappings', {})

class Template(common.Template):
    packaged_version = '3.3.4'
    summary                    = 'Template for creating a plone3 project'
    python                     = 'python-2.4'
    default_template_package   = 'ZopeSkel'
    default_template_epn       = 'paste.paster_create_template'
    default_template_templaten = 'plone3_buildout'
    init_messages = (
        '%s' % (
            '---------------------------------------------------------\n'
            '\tPlone 3 needs a python 2.4 to run:\n'
            '\t * if you do not fill anything, it will use minitage or system\'s one\n'
            '\t * if you do not provide one explicitly, it will use minitage or system\'s one\n'
            '\t * Bindings will be automaticly included when you choose for example relstorage/mysql or plone ldap support.\n'
            '\tAditionnaly you ll got two buildouts for production (buildout.cfg) and develoment mode (dev.cfg).\n'
            '\tYou can also activate or safely ignore questions about zeoserver and relstorage if you do not use them.\n'
            '---------------------------------------------------------\n'
        ),
    )
    # not nice, but allow us to import variables from another place like
    # from plone3 import qi_mappings and also avoid template copy/paste,
    # just inherit and redefine those variables in the child class.
    # plone quickinstaller option/names mappings

    # buildout <-> minitage config vars mapping
    sections_mappings = {
        'additional_eggs': eggs_mappings,
        'plone_zcml': zcml_mappings,
        'plone_products': urls_mappings,
        'plone_np': plone_np_mappings,
        'plone_vsp': plone_vsp_mappings,
        'plone_scripts': scripts_mappings,
    }
    qi_mappings               = qi_mappings
    z2packages                = z2packages
    z2products                = z2products
    addons_vars               = addons_vars
    eggs_mappings             = eggs_mappings
    scripts_mappings          = scripts_mappings
    zcml_loading_order        = zcml_loading_order
    zcml_mappings             = zcml_mappings
    versions_mappings         = versions_mappings
    checked_versions_mappings = checked_versions_mappings
    urls_mappings             = urls_mappings
    plone_np_mappings         = plone_np_mappings
    plone_vsp_mappings        = plone_vsp_mappings

    def read_vars(self, command=None):
        if command:
            if not command.options.quiet:
                for msg in getattr(self, 'init_messages', []):
                    print msg
        vars = common.Template.read_vars(self, command)
        for i, var in enumerate(vars[:]):
            if var.name in ['relstorage_dbname', 'relstorage_dbuser'] and command:
                vars[i].default = command.args[0]
        return vars

    def pre(self, command, output_dir, vars):
        """register catogory, and roll in common,"""
        vars['plonesite'] = common.SPECIALCHARS.sub('', vars['project'])
        vars['category'] = 'zope'
        vars['includesdirs'] = ''
        vars['hr'] = '#' * 120
        common.Template.pre(self, command, output_dir, vars)
        vars['mode'] = vars['mode'].lower().strip()

        # transforming eggs requirements as lists
        for var in self.sections_mappings:
            if var in vars:
                vars[var] = [a.strip() for a in vars[var].split(',')]

        # ZODB3 from egg
        vars['additional_eggs'].append('#ZODB3 is installed as an EGG!')
        vars['additional_eggs'].append('ZODB3')

        # plone system dependencies
        if vars['inside_minitage']:
            for i in ['libxml2', 'libxslt', 'pilwotk', 'libiconv']:
                vars['opt_deps'] += ' %s' %  search_latest('%s.*' % i, vars['minilays'])

        # databases
        minitage_dbs = ['mysql', 'postgresql']
        for db in minitage_dbs:
            if vars['with_database_%s' % db] and vars['inside_minitage']:
                vars['opt_deps'] += ' %s' % search_latest('%s-\d\.\d*'% db, vars['minilays'])

        # openldap
        if vars['with_binding_ldap'] and vars['inside_minitage']:
            cs = search_latest('cyrus-sasl-\d\.\d*', vars['minilays'])
            vars['opt_deps'] += ' %s %s' % (
                search_latest('openldap-\d\.\d*', vars['minilays']),
                cs
            )
            vars['includesdirs'] = '\n    %s'%  os.path.join(
                vars['mt'], cs, 'parts', 'part', 'include', 'sasl'
            )

        # haproxy
        if vars['with_haproxy'] and vars['inside_minitage']:
            vars['opt_deps'] += ' %s' % search_latest('haproxy-\d\.\d*', vars['minilays'])

        # relstorage
        if 'relstorage' in vars['mode']:
            vars['additional_eggs'].append('#Relstorage')
            vars['additional_eggs'].append('Relstorage')
            for db in [var.replace('with_database_', '')
                        for var in vars
                        if 'with_database_' in var]:
                if db in vars['relstorage_type']:
                    vars['additional_eggs'].extend(
                        [a
                         for a in eggs_mappings['with_database_%s'%db]
                         if not a in vars['additional_eggs']
                        ]
                    )
                    if db in minitage_dbs and vars['inside_minitage']:
                        vars['opt_deps'] += ' %s' % search_latest('%s-\d\.\d*'% db, vars['minilays'])

        # do we need some pinned version
        vars['plone_versions'] = []
        for var in self.versions_mappings:
            vars['plone_versions'].append(('# %s' % var, '',))
            for pin in self.versions_mappings[var]:
                vars['plone_versions'].append(pin)

        if vars["with_checked_versions"]:
            for var in self.checked_versions_mappings:
                if vars[var]:
                    vars['plone_versions'].append(('# %s' % var, '',))
                    for pin in self.checked_versions_mappings[var]:
                        vars['plone_versions'].append(pin)

        if not vars['mode'] in ['zodb', 'relstorage', 'zeo']:
            raise Exception('Invalid mode (not in zeo, zodb, relstorage')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        for section in self.sections_mappings:
            for var in [k for k in self.sections_mappings[section] if vars[k]]:
                if not section == 'plone_zcml':
                    vars[section].append('#%s'%var)
                for item in self.sections_mappings[section][var]:
                   if section == 'plone_zcml':
                       item = '-'.join(item)
                   if not '%s\n' % item in vars[section]:
                       if not item in vars[section]:
                           vars[section].append(item)


        package_slug_re = re.compile('(.*)-(meta|configure|overrides)', common.reflags)
        def zcmlsort(obja, objb):
            obja = re.sub('^#', '', obja).strip()
            objb = re.sub('^#', '', objb).strip()
            ma, mb = package_slug_re.match(obja), package_slug_re.match(objb)
            if not obja:
                return 1
            if not objb:
                return -1
            apackage, aslug = (obja, 'configure')
            if ma:
                apackage, aslug = ma.groups()
            bpackage, bslug = (objb, 'configure')
            if mb:
                bpackage, bslug = mb.groups()
            aorder = self.zcml_loading_order.get((apackage, aslug), 50000)
            border = self.zcml_loading_order.get((bpackage, bslug), 50000)
            return aorder - border

        # order zcml
        vars["plone_zcml"].sort(zcmlsort)
        vars["plone_zcml"] = [a for a in  vars["plone_zcml"] if a.strip()]

        # add option marker
        for option in self.zcml_mappings:
            for p in self.zcml_mappings[option]:
                id = '-'.join(p)
                if id in vars['plone_zcml']:
                    i = vars['plone_zcml'].index(id)
                    vars['plone_zcml'][i:i] = ['#%s' % option]
        vars['plone_zcml'][0:0] = ['']

        cwd = os.getcwd()
        if not os.path.exists(self.output_dir):
            self.makedirs(self.output_dir)
        # install also the official template from ZopeSkel, setting its variables
        vars['plone_products_install'] = ''
        vars['zope2_install'] = ''
        vars['debug_mode'] = 'off'
        vars['verbose_security'] = 'off'

        # running default template (like plone3_buildout) and getting stuff from it.
        try:
            if not getattr(self, 'default_template_package', None):
                raise NoDefaultTemplateError('')

            ep = pkg_resources.load_entry_point(
                self.default_template_package,
                self.default_template_epn,
                self.default_template_templaten
            )
            p3 = ep(self)
            coo = command.options.overwrite
            command.options.overwrite = True
            def null(a, b, c):
                pass
            p3.post = null
            p3.check_vars(vars, command)
            p3.run(command, vars['path'], vars)
            command.options.overwrite = coo
            self.post_default_template_hook(command, output_dir, vars, p3)
        except NoDefaultTemplateError, e:
            pass
        except Exception, e:
            print 'Error executing plone3 buildout, %s'%e

        # be sure our special python is in priority
        vars['opt_deps'] = re.sub('\s*%s\s*' % self.python, ' ', vars['opt_deps'])
        vars['opt_deps'] += " %s" % self.python
        vars['http_port1'] = int(vars['http_port']) + 1
        vars['http_port2'] = int(vars['http_port']) + 2
        vars['http_port3'] = int(vars['http_port']) + 3
        vars['http_port4'] = int(vars['http_port']) + 4
        vars['http_port5'] = int(vars['http_port']) + 5
        vars['running_user'] = common.running_user
        vars['instances_description'] = common.INSTANCES_DESCRIPTION % vars

    def post_default_template_hook(command, output_dir, vars, ep):
        try:
            etc = os.path.join(vars['path'], 'etc', 'plone')
            if not os.path.isdir(etc):
                os.makedirs(etc)
            cfg = os.path.join(vars['path'], 'buildout.cfg')
            dst = os.path.join(vars['path'],
                               'etc', 'plone', 'plone3.buildout.cfg')
            vdst = os.path.join(vars['path'],
                               'etc', 'plone', 'plone3.versions.cfg')
            bc = ConfigParser()
            bc.read(cfg)
            ext = ''
            try:
                ext = bc.get('buildout', 'extends')
            except:
                pass
            if ext:
                try:
                    open(vdst, 'w').write(
                        urllib2.urlopen(ext).read()
                    )
                except Exception, e:
                    shutil.copy2(
                        pkg_resources.resource_filename(
                            'minitage.paste',
                            'projects/plone3/versions.cfg'
                        ),
                        vdst
                    )
                    self.lastlogs.append(
                        "Versions have not been fixed, be ware. Are"
                        " you connected to the internet (%s).\n" % e
                    )
                    self.lastlogs.append(
                        "%s" % (
                            'As a default, we will take an already'
                            ' downloaded versions.cfg matching plone'
                            ' %s.\n' %
                            self.packaged_version
                        )
                    )
            os.rename(cfg, dst)
            # remove the extends bits in the plone3 buildout
            if not bc.has_section('buildout'):
                bc.add_section('buildout')
            bc.set(
                'buildout',
                'extends',
                'plone3.versions.cfg'
            )
            bc.write(open(dst, 'w'))
        except Exception, e:
            print
            print
            print "%s" % ("Plone folks have changed their paster, we didnt get any"
                           " buildout, %s" %e)
            print
            print


sd_str = '%s' % (
    'Singing & Dancing NewsLetter, see http://plone.org/products/dancing'
    ' S&D is known to lead to multiple buildout installation errors.'
    ' Be sure to activate it and debug the errors. y/n'
)

Template.vars = common.Template.vars \
        + [var('plone_version', 'Plone version, default is the one supported and packaged', default = Template.packaged_version,),
           var('address', 'Address to listen on', default = 'localhost',),
           var('http_port', 'Port to listen to', default = '8081',),
           var('mode', 'Mode to use : zodb|relstorage|zeo', default = 'zodb'),
           var('zeo_address', 'Address for the zeoserver (zeo mode only)', default = 'localhost:8100',),
           var('zope_user', 'Administrator login', default = 'admin',),
           var('zope_password', 'Admin Password in the ZMI', default = 'secret',),
           var('relstorage_type', 'Relstorage database type (only useful for relstorage mode)', default = 'postgresql',),
           var('relstorage_host', 'Relstorage database host (only useful for relstorage mode)', default = 'localhost',),
           var('relstorage_port', 'Relstorage databse port (only useful for relstorage mode). (postgresql : 5432, mysql : 3306)', default = '5432',),
           var('relstorage_dbname', 'Relstorage databse name (only useful for relstorage mode)', default = 'minitagedb',),
           var('relstorage_dbuser', 'Relstorage user (only useful for relstorage mode)', default = common.running_user),
           var('relstorage_password', 'Relstorage password (only useful for relstorage mode)', default = 'secret',),
           var('solr_host', 'Solr host (only useful if you want solr)', default = '127.0.0.1',),
           var('solr_port', 'Solr port (only useful if you want solr)', default = '8983',),
           var('solr_path', 'Solr path (only useful if you want solr)', default = '/solr',),
           var('with_supervisor', 'Supervisor support (monitoring), http://supervisord.org/ y/n', default = 'y',),
           var('supervisor_host', 'Supervisor host', default = '127.0.0.1',),
           var('supervisor_port', 'Supervisor port', default = '9001',),
           var('with_haproxy', 'haproxy configuration file generation support (loadbalancing), http://haproxy.1wt.eu/ y/n', default = 'y',),
           var('haproxy_host', 'Haproxy host', default = '127.0.0.1',),
           var('haproxy_port', 'Haproxy port', default = '8201',),
           var('plone_products', 'comma separeted list of adtionnal products to install: eg: file://a.tz file://b.tgz', default = '',),
           var('additional_eggs', 'comma separeted list of additionnal eggs to install', default = '',),
           var('plone_zcml', 'comma separeted list of eggs to include for searching ZCML slugs', default = '',),
           var('plone_np', 'comma separeted list of nested packages for products distro part', default = '',),
           var('plone_vsp', 'comma separeted list of versionned suffix packages for product distro part', default = '',),
           var('plone_scripts', 'comma separeted list of scripts to generate from installed eggs', default = '',),
           var('with_checked_versions', 'Use product versions that interact well together (can be outdated, check [versions] in buildout.', default = 'n',),
           ] + Template.addons_vars

# vim:set et sts=4 ts=4 tw=0:
