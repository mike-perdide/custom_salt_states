import logging

log = logging.getLogger(__name__)

import salt
import difflib


def _error(ret, err_msg):
    ret['result'] = False
    ret['comment'] = err_msg
    return ret


def _get_template_texts(source_list=None,
                        template='jinja',
                        defaults=None,
                        context=None,
                        env='base',
                        **kwargs):
    '''
    Iterate a list of sources and process them as templates.
    Returns a list of 'chunks' containing the rendered templates.
    Taken directly from salt's file.py state module.
    '''

    ret = {'name': '_get_template_texts',
           'changes': {},
           'result': True,
           'comment': '',
           'data': []}

    if source_list is None:
        return _error(ret,
                      '_get_template_texts called with empty source_list')

    txtl = []

    for (source, source_hash) in source_list:

        tmpctx = defaults if defaults else {}
        if context:
            tmpctx.update(context)
        rndrd_templ_fn = __salt__['cp.get_template'](source, '',
                                  template=template, env=env,
                                  context=tmpctx, **kwargs)
        msg = 'cp.get_template returned {0} (Called with: {1})'
        log.debug(msg.format(rndrd_templ_fn, source))
        if rndrd_templ_fn:
            tmplines = None
            with salt.utils.fopen(rndrd_templ_fn, 'rb') as fp_:
                tmplines = fp_.readlines()
            if not tmplines:
                msg = 'Failed to read rendered template file {0} ({1})'
                log.debug(msg.format(rndrd_templ_fn, source))
                ret['name'] = source
                return _error(ret, msg.format(rndrd_templ_fn, source))
            txtl.append(''.join(tmplines))
        else:
            msg = 'Failed to load template file {0}'.format(source)
            log.debug(msg)
            ret['name'] = source
            return _error(ret, msg)

    ret['data'] = txtl
    return ret


def contains(name,
             text=None,
             makedirs=False,
             source=None,
             source_hash=None,
             __env__='base',
             template='jinja',
             sources=None,
             source_hashes=None,
             defaults=None,
             context=None):
    """
    This does what I'd like file.append to do: when using a source, if the
    lines from the source are in the target file, even if they are not in
    the same order, do nothing. If some lines are not present in the target
    file, only these will be appended.

    TODO:
        - add an option to force the order
        - support the other options of file.append
    """
    ret = {
        'name': name,
        'changes': {},
        'result': True,
        'comment': "",
    }
    source_list = [(source, None)]
    templates_content = _get_template_texts(
        source_list=source_list,
        template="jinja",
        defaults=defaults,
        context=context,
        env=__env__,
    )
    with salt.utils.fopen(name, 'rb') as fp_:
        source_lines = fp_.readlines()

    lines_that_must_appear = []
    _lines = templates_content['data'][0].split("\n")
    for line in _lines:
        if line != _lines[-1]:
            line += "\n"
        lines_that_must_appear.append(line)

    if len(lines_that_must_appear) == 0:
        return ret

    lines_to_append_list = []
    for line in lines_that_must_appear:
        if line not in source_lines:
            lines_to_append_list.append(line)
    ret['comment'] = str(lines_to_append_list) + "==" + str(source_lines)

    with salt.utils.fopen(name, 'a') as fp_:
        for line in lines_to_append_list:
            fp_.write(line)

    with salt.utils.fopen(name, 'rb') as fp_:
        end_lines = fp_.readlines()

    if source_lines != end_lines:
        ret['changes']['diff'] = (
            "".join(difflib.unified_diff(source_lines, end_lines,))
        )

    return ret
