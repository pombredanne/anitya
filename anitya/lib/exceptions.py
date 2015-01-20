#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

anitya exceptions.
"""


class AnityaException(Exception):
    ''' Generic class covering all the exceptions generated by anitya. '''
    pass


class AnityaPluginException(AnityaException):
    ''' Generic exception class that can be used by the plugin to indicate
    an error.
    '''
    pass
