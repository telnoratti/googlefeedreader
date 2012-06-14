#!/usr/bin/python2
import logging
import urllib
import urllib2
from urlparse import urlparse
import re
import functools
from GoogleReader import  CONST
from GoogleReader.reader import GoogleReader
from embers import Data, session

diariocolatinofix = re.compile(r'\?tpl=[0-9]+')

def verify_num_tags():
    pass
    # TODO

def set_up():
    gr = GoogleReader()
    gr.identify()
    gr.login()
    return gr

def format_url(url):
    """Google stores the url without duplicate // in the body and without trailing /'s. Also, www. is optional.
    We remove www. for simplicity.
    ----
    This function caused more problems than it fixed and was removed
    """
    #if url[7:11] == 'www.':
    #    # TODO possibly get rid of this if it breaks something
    #    # It broke some of the feeds.
    #    url = url[11:]
    #else:
    #    url = url[7:]
    #return url.replace('//', '/')

def do_line(gr, line, line_num):
    split = line.rstrip().split(',')
    # remove www. and right / from home page for consistency and percent quote homepage
    # TODO add support for https and urls that don't include http
    home_page = urlparse(split[0]).netloc.rsplit(':', 1)[0]

    if split[3] == 'N/A':
        country = 'none'
    else:
        country = split[3]

    logging.info("%s %s" % (str(line_num), line.rstrip()))
    result = gr.add_subscription(url=split[1], labels=['home_page:' + 
            home_page.encode('utf-8'), 'country:' + country])
    return result

def log_feed(line_num, job):
    if job.exception():
        logging.error('%d %r' % (line_num, job.exception()))
    else:
        logging.info('%d %s\n' % (line_num, job.result()))

def add_to_database():
        gr = set_up()
        logging.info('Importing Unread Feeds')
        entries = gr.get_unread().get_entries()
        while entries:
            for entry in entries:
                if Data.select().filter_by(url = entry['link']).count() > 0:
                    logging.warn(entry['link'] + ' found in database already from '
                            + entry['sources'])
                    continue
                try:
                    #This is for one site that if the link is unalterd it loops back to the rss feed.
                    entry['link'] = re.sub(diariocolatinofix, '', entry['link'])
                    f = urllib2.urlopen(entry['link'])
                    article = f.read()
                except urllib2.HTTPError as e:
                    logging.exception('HTTPError %i -- %s' % (e.code, entry['link']))
                except urllib2.URLError as e:
                    logging.exception('URLError %s -- %s' % (e.reason, entry['link']))
                d = Data(0, "http://localhost", unicode(article, errors='replace'))
                d.other['author'] = "Calvin Winkowski"
                d.other['feed'] = unicode(str(entry), errors='replace')
                source = ''
                country = ''
                for i in entry['categories']:
                    if i.startswith('user/-/label/country:'):
                        country = i[-2:]
                    elif i.startswith('user/-/label/home_page:'):
                        source = i[23:]
                d.other['source'] = unicode(source)
                d.other['country'] = unicode(country)
                d.url = entry['link']
                d.add()
                session.commit()
                gr.set_read(entry['google_id'])
                logging.info(entry['link'] + ' added to database.')
            entries = gr.get_unread().get_entries()

def add_to_reader():
    gr = set_up()
    logging.info('User set up.')
#    with futures.ThreadPoolExecutor(max_workers=10) as executor:
#        for line_num, line in enumerate(open('newsiterss.txt')):
#            job = executor.submit(do_line, gr, line, line_num)
#            job.add_done_callback(functools.partial(log_feed, line_num))

    for line_num, line in enumerate(open('newsiterss.txt')):
        try:
            logging.info('%d %s\n' % (line_num, do_line(gr, line, line_num)))
        except Exception as e:
            logging.error('%d %r' % (line_num, e))

#def get_total_count():
    

if __name__ == '__main__':
    import argparse
    import datetime

    log_file = 'logs/' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + '.log'
    logging.basicConfig(filename=log_file, filemode='w', level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    logging.info('Program Started')

    parser = argparse.ArgumentParser(description='Interface with Google Reader.')
    parser.add_argument('--clean', action='store_true', default=False, help='erases all entries and tags from Google Reader.')
    parser.add_argument('--new', action='store_true', default=False, help='List new entries.')
    parser.add_argument('--read', action='store_true', default=False, help='Import new articles into database.')
    parser.add_argument('--add', action='store_true', default=False, help='Add new feeds into reader')
    args = parser.parse_args()
    if args.clean:
        gr = set_up()
        logging.info('Google Reader Cleaned.')
        gr.del_all_subscriptions()
        gr.disable_all_tags()
    elif args.new:
        gr = set_up()
        logging.info('Reading an entry.')
        for entry in gr.get_unread().get_entries():
            logging.info('Unread: %s -- %s' % (entry['published'], entry['link']))
    elif args.read:
        add_to_database()
    elif args.add:
        add_to_reader()
    elif args.count:
        get_total_count()
    logging.info('Program Terminated')




