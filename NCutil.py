#!/usr/bin/python
##############################
######### IMPORTS ############
import sys
import argparse
import os
import subprocess
import sqlite3

from platform import mac_ver
from glob import glob

##############################
######## FUNCTIONS ###########
def usage():
    return """
  _  _  ___     _   _ _ 
 | \| |/ __|  _| |_(_) |
 | .` | (_| || |  _| | |
 |_|\_|\___\_,_|\__|_|_|

Copyright 2014. Jacob Salmela.  http://jacobsalmela.com
Modified + OSX 10.10 Yosemite Support,  Jason Johnson (2015)"""


def get_osx_major():
    '''Return OS X version in format of 10.x.x'''
    v, _, _ = mac_ver()
    #Parse Out Major Version, mac_ver() can produce 10.10.2, 10.9.5, 10.8..
    return v.split('.')[0] + "." + v.split('.')[1]


def get_nc_db():
    '''Returns a path to the current (hopefully?) NotificationCenter db'''
    nc_db = None
    osx_major = get_osx_major()
    if osx_major == '10.8' or osx_major == '10.9':
        nc_nb_path = os.path.expanduser(
            '~/Library/Application Support/NotificationCenter/')
        nc_dbs = glob(nc_nb_path + '*.db')
        if nc_dbs:
            nc_dbs.sort(key=os.path.getmtime)
            # most recently modified will be the last one
            nc_db = nc_dbs[-1]
    # Support for osx 10.10 added via randomly generated id for
    # Notification Center Database
    elif osx_major == '10.10':
        darwin_user_dir = subprocess.check_output(
            ['/usr/bin/getconf', 'DARWIN_USER_DIR']).rstrip()
        nc_db = os.path.join(
            darwin_user_dir, 'com.apple.notificationcenter/db/db')
    return nc_db


def connect_to_db():
    '''Connect to the Notification Center db and return connection object
    and cursor'''
    conn = None
    curs = None
    #Connect To SQLLite
    nc_db = get_nc_db()
    if nc_db:
        conn = sqlite3.connect(nc_db)
        conn.text_factory = str
        curs = conn.cursor()
    return conn, curs


def kill_notification_center():
    '''Send a kill signal to NotificationCenter and usernoted; they will
    relaunch'''
    subprocess.call(['/usr/bin/killall', 'NotificationCenter'])
    subprocess.call(['/usr/bin/killall', 'usernoted'])


def commit_changes(conn):
    '''Apply the changes and close the sqlite connection'''
    conn.commit()
    conn.close()


def verboseOutput(*args):
    #------------------------
    if verbose:
        try:
            print "Verbose:", args
        except:
            pass


def list_clients():
    '''List all bundleids in database'''
    conn, curs = connect_to_db()
    curs.execute("select bundleid from app_info")
    for row in curs.fetchall():
        print row[0]
    conn.close()


def get_available_id(curs):
    '''Get the highest app_id, then increment'''
    curs.execute("select app_id from app_info")
    # return first field of last row
    last_id = curs.fetchall()[-1][0]
    return last_id + 1


def insert_app(bundle_ids):
    '''Adds bundle_ids to Notification Center database'''
    conn, curs = connect_to_db()
    for bundle_id in bundle_ids:
        if not bundleid_exists(bundle_id):
            next_id = get_available_id(curs)
            curs.execute("INSERT INTO app_info VALUES('%s', '%s', '14', '5', '%s')"
                         % (next_id, bundle_id, next_id))
        else:
            print >> sys.stderr, "%s is already in Notification Center" % bundle_id

    commit_changes(conn)
    kill_notification_center()


def remove_app(bundle_ids):
    '''Removes bundle_ids from Notification Center database'''
    conn, curs = connect_to_db()
    for bundle_id in bundle_ids:
        if not bundleid_exists(bundle_id):
            print >> sys.stderr, (
                "WARNING: %s not in Notification Center" % bundle_id)
        else:
            curs.execute("DELETE from app_info where bundleid IS '%s'" % (bundle_id))

    commit_changes(conn)
    kill_notification_center()


def set_flags(flags, bundle_id):
    '''Sets Notification Center flags for bundle_id'''
    conn, curs = connect_to_db()
    curs.execute("UPDATE app_info SET flags='%s' where bundleid='%s'"
                  % (flags, bundle_id))
    commit_changes(conn)


def bundleid_exists(bundle_id):
    '''Returns a boolean telling us if the bundle_id is in the database.'''
    conn, curs = connect_to_db()
    curs.execute("SELECT bundleid from app_info WHERE bundleid IS '%s'"
                 % bundle_id)
    matching_ids = [row[0] for row in curs.fetchall()]
    conn.close()
    return len(matching_ids) > 0


def get_matching_ids(match_string):
    '''Returns any bundle_ids matching the match_string'''
    conn, curs = connect_to_db()
    curs.execute("SELECT bundleid from app_info WHERE bundleid LIKE '%s'"
                 % match_string)
    matching_ids = [row[0] for row in curs.fetchall()]
    conn.close()
    return matching_ids


def get_flags(bundle_id):
    '''Returns flags for bundle_id'''
    conn, curs = connect_to_db()
    curs.execute("SELECT flags from app_info where bundleid='%s'" % (bundle_id))
    try:
        flags = curs.fetchall()[0][0]
    except IndexError:
        flags = 0
    conn.close()
    return int(flags)


def remove_system_center():
    '''Sets alert style to 'none'' for all bundle_ids starting with
    _SYSTEM_CENTER_:. Not convinced this is a great idea, but there it is...'''
    set_alert('none', get_matching_ids('_SYSTEM_CENTER_:%'))


# flags are bits in a 16 bit(?) data structure
SHOW_IN_CENTER = 1 << 0
BADGE_ICONS = 1 << 1
SOUNDS = 1 << 2
BANNER_STYLE = 1 << 3
ALERT_STYLE = 1 << 4
UNKNOWN_5 = 1 << 5
UNKNOWN_6 = 1 << 6
UNKNOWN_7 = 1 << 7
UNKNOWN_8 = 1 << 8
UNKNOWN_9 = 1 << 9
UNKNOWN_10 = 1 << 10
UNKNOWN_11 = 1 << 11
SHOW_ON_LOCKSCREEN = 1 << 12
SHOW_PREVIEWS_ALWAYS = 1 << 13
SHOW_PREVIEWS_WHEN_UNLOCKED = 1 << 14
UNKNOWN_15 = 1 << 15


def get_alert_style(bundle_id):
    '''Print the alert style for bundle_id'''
    if not bundleid_exists(bundle_id):
        print >> sys.stderr, "%s not in Notification Center" % bundle_id
        exit(1)

    current_flags = get_flags(bundle_id)
    if current_flags & ALERT_STYLE:
        style = "alerts"
    elif current_flags & BANNER_STYLE:
        style = "banners"
    else:
        style = "none"
    print "%s has notification style: %s" % (bundle_id, style)


def set_alert(style, bundle_ids):
    '''Set the alert style for bundle_id. If kill_nc is False, skip killing
    the NotificationCenter and usernoted processes'''

    # verify this is a supported alert type
    if style not in ['none', 'alerts', 'banners']:
        print >> sys.stderr, "%s is not a valid alert type" % style
        exit(1)

    if not bundle_ids:
        print >> sys.stderr, "Must specify at least one bundle id!"
        exit(1)

    for bundle_id in bundle_ids:
        if not bundleid_exists(bundle_id):
            print >> sys.stderr, (
                "WARNING: %s not in Notification Center" % bundle_id)
        else:
            current_flags = get_flags(bundle_id)
            # turn off both banner and alert flags
            new_flags = current_flags & ~(BANNER_STYLE | ALERT_STYLE)
            if style == 'alerts':
                # turn on alert flag
                new_flags = new_flags | ALERT_STYLE
            elif style == 'banners':
                # turn on banner flag
                new_flags = new_flags | BANNER_STYLE
            if new_flags != current_flags:
                set_flags(new_flags, bundle_id)
    kill_notification_center()


def main():
    '''Define and parse options, call our worker functions'''
    parser = argparse.ArgumentParser(usage=usage())
    parser.add_argument('--list', '-l', action='store_true',
                        help='List BUNDLE_IDs in Notification Center database.')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='More verbose output from this tool.')
    parser.add_argument('--insert', '-i', metavar='BUNDLE_ID [...]', nargs='+',
                        help='Add BUNDLE_IDs to Notification Center.')
    parser.add_argument('--remove', '-r', metavar='BUNDLE_ID [...]', nargs='+',
                        help='Remove BUNDLE_IDs from Notification Center.')
    parser.add_argument('--remove-system-center', action='store_true',
                        help='Set notification style to \'none\' for all '
                        '_SYSTEM_CENTER_ items.')
    parser.add_argument('--get-alert-style', '-g', metavar='BUNDLE_ID',
                        help='Get current notification style for BUNDLE_ID.')
    parser.add_argument('--alert-style', '-a',
                        metavar='ALERT_STYLE BUNDLE_ID [...]', nargs='+',
                        help='Set notification style for BUNDLE_IDS. Supported '
                        'styles are none, banners, and alerts.')
    options = parser.parse_args()

    if options.list:
        list_clients()
    elif options.insert:
        insert_app(options.insert)
    elif options.remove:
        remove_app(options.remove)
    elif options.remove_system_center:
        remove_system_center()
    elif options.get_alert_style:
        get_alert_style(options.get_alert_style)
    elif options.alert_style:
        set_alert(options.alert_style[0], options.alert_style[1:])
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
