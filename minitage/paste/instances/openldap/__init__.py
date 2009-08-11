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
import stat
import getpass
import pwd
import grp
import re
import subprocess
import sha
import md5
import base64

from minitage.paste.instances import common
from minitage.core.common import remove_path
from paste.script import templates

re_flags = re.M|re.U|re.I|re.S

def SSHA_password ( password ):
    p_ssha = sha.new( password )
    p_ssha.update( password )
    p_ssha_base64 = base64.encodestring(p_ssha.digest() + password + '' )
    return '%s%s' %( '{SSHA}', p_ssha_base64 )
def MD5_password ( password ):
    p_md5 = md5.new( password )
    return '%s%s' %( '{MD5}', base64.encodestring(p_md5.digest()))




class Template(common.Template):

    summary = 'Template for creating a openldap instance'
    _template_dir = 'template'
    use_cheetah = True
    pg_present = False

    def pre(self, command, output_dir, vars):
        common.Template.pre(self, command, output_dir, vars)
        vars['db_password'] = MD5_password(vars['db_password'])

    def post(self, command, output_dir, vars):
        sys = vars['sys']
        dirs = [os.path.join(sys, 'bin'),
                os.path.join(sys, 'etc', 'init.d')]
        for directory in dirs:
            for filep in os.listdir(directory):
                p = os.path.join(directory, filep)
                os.chmod(p, stat.S_IRGRP|stat.S_IXGRP|stat.S_IRWXU)

        infos = "%s" % (
            "    * You can look for wrappers to various openldap scripts located in %s. You must use them as they are configured to use some useful defaults to connect to your database.\n"
            "    * A configuration file for your openldap instance has been created in %s.\n"
            "    * A init script to start your server is available in %s.\n"
            "    * A logrotate configuration file to handle your logs can be linked in global scope, it is available in %s.\n"
            "    * The datadir is located under %s\n"
            "" % (
                '"%s'%os.path.join(
                    vars['sys'], 'bin', '%s.%s.*" eg : %s.%s.ldapadd' % (
                        vars['db_orga'],
                        vars['db_suffix'],
                        vars['db_orga'],
                        vars['db_suffix']
                    )
                ),
                os.path.join(
                    vars['sys'], 'etc', 'openldap',
                    '%s_%s.%s-slapd.conf' % (
                        vars['project'],
                        vars['db_orga'], vars['db_suffix']
                    )
                ),
                os.path.join(
                    vars['sys'], 'etc', 'init.d', 'openldap_%s_%s.%s' %(
                        vars['project'], vars['db_orga'], vars['db_suffix']
                    )
                ),
                os.path.join(
                    vars['sys'], 'etc', 'logrotate.d', '%s_%s.%s.openldap' %(
                        vars['project'], vars['db_orga'], vars['db_suffix']
                    )
                ),
                os.path.join(
                    vars['sys'], 'var', 'data',
                    'openldap',
                    '%s_%s.%s.' % (
                        vars['project'], vars['db_orga'], vars['db_suffix']
                    )
                )
            )
        )
        README = os.path.join(vars['path'],
                              'README.openldap.%s-%s.%s' % (
                                  vars['project'],
                                  vars['db_orga'],
                                  vars['db_suffix']
                              )
                             )
        open(README, 'w').write(infos)
        print "Installation is now finished."
        print infos
        print "Those informations have been saved in %s." % README

Template.required_templates = ['minitage.instances.env']
running_user = getpass.getuser()
gid = pwd.getpwnam(running_user)[3]
#group = grp.getgrgid(gid)[0]
Template.vars = common.Template.vars + \
        [
            templates.var('db_host', 'Host to listen on', default = 'localhost'),
            templates.var('db_suffix', 'Suffix for the organization to create', default = 'org'),
            templates.var('db_orga', 'Organization node name to create', default='domain'),
            templates.var('db_port', 'Port to listen to', default = '389'),
            templates.var('db_user', 'LDAP Super user', default = running_user),
            templates.var('db_password', 'LDAP Super user password', default = running_user),
            templates.var('ol_version', 'OPENLDAP version', default = '2.4'),
        ]
# vim:set et sts=4 ts=4 tw=80:
