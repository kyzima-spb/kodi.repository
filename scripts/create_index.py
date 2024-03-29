import itertools
import os
import sys


public_dir = sys.argv[1]

for path, dirs, files in os.walk(public_dir):
    links = itertools.chain(
        [('%s/' % i, i) for i in dirs],
        [(i, i) for i in files if i.endswith('.zip')]
    )
    with open(os.path.join(path, 'index.html'), 'w') as f:
        f.write('<pre>')
        path != public_dir and f.write('<a href="../">..</a>\n')
        f.write('\n'.join('<a href="%s">%s</a>' % (url, text) for url, text in links))
        f.write('</pre>')
