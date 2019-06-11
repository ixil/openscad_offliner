'''
-------------------------------------------------------------------------
openscad_offliner.py: Download OpenSCAD online doc for offline reading

Copyright (C) 2019 Oliver Harley (oliver.r.harley+git gmail.com) 
Copyright (C) 2015 Runsun Pan (run+sun (at) gmail.com) 
Source: https://github.com/runsun/faces.scad
This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License along 
with this program; if not, see <http://www.gnu.org/licenses/gpl-2.0.html>
-------------------------------------------------------------------------

Require: python 3, BeautifulSoup

Usage:
		1) Save this file in folder x.
		2) In folder x, type: 
			
			  python openscad_offliner.py 
		All web pages will be saved in x/openscad_docs, 
		and all images in x/openscad_docs/imgs  

Note: 

	1) All html pages are stored in dir_docs (default: openscad_docs)
	2) All images are stored in dir_imgs (default: openscad_docs/imgs)
	3) All OpenSCAD-unrelated stuff, like wiki menu, etc, are removed
	4) All wiki warnings sign are removed
	5) Search box is hidden. There might be a way (i.e., javascript) to 
		search the doc but we leave that to the future.
        6) Probably some script at the end to modify the urls in the index page

git: https://github.com/runsun/openscad_offliner

'''




#!/usr/bin/env python
# -*- coding: utf-8 -*-

import errno
import logging
import os
import pickle
import time
import urllib
from collections import defaultdict
from os import walk
from urllib.parse import urlparse

from bs4 import BeautifulSoup as bs

cheatsheet_url = "https://www.openscad.org/cheatsheet/index"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
HAMMERTIME = False

# taken from https://github.com/runsun/openscad_offliner/blob/master/openscad_offliner.py
this_dir = os.path.dirname(os.path.abspath(__file__))
dir_docs = 'openscad_docs'
dir_imgs = os.path.join(dir_docs, 'imgs')
dir_styles = 'styles'
dir_styles_full = os.path.join(dir_docs, 'styles')
offline_cheatsheet = 'openscad_offline_cheatsheet.html'

url_openscadorg = 'https://www.openscad.org'
url_wiki = 'https://en.wikibooks.org'
url_openscadwiki = '/wiki/OpenSCAD_User_Manual'
url_offliner = 'https://github.com/ixil/openscad_offliner'
if not os.path.exists(dir_docs): os.makedirs(dir_docs)
if not os.path.exists(dir_imgs): os.makedirs(dir_imgs)
if not os.path.exists(dir_styles_full): os.makedirs(dir_styles_full)

print("\n[Local]")
print("this_dir= " + this_dir)
print("dir_docs= " + dir_docs)
print("dir_imgs= " + dir_imgs)
print("dir_styles= " + dir_styles)
print("dir_styles_full= " + dir_styles_full)
print("cheatsheet page= " + offline_cheatsheet)
print()

#
# Buffer to keep track of downloaded to avoid repeating downloads
#
pages = []  # Urls of downloaded pages
imgs = []  # Local paths of downloaded images
styles = []  # stylesheet urls


def populate(buffer_fp=os.path.join(dir_docs, 'buffers.txt')):
    ''' This is mostly useless as it will not work unless the program has finished to completion -
    and appending write-line style would be better.'''
    with open(buffer_fp, 'wb+') as f:
        pickle.dump({'pages': pages, 'imgs': imgs, 'styles': styles}, f)
        logger.info("writing buffers out")


def prepopulate(buffer_fp=os.path.join(dir_docs, 'buffers.txt')):
    ''' This is mostly useless as we do not reparse the files at all.'''
    try:
        with open(buffer_fp, 'rb') as fp:
            buffers = pickle.load(fp)

        pages.extend(buffers['pages'])
        imgs.extend(buffers['imgs'])
        styles.extend(buffers['styles'])
    except FileNotFoundError:
        pass


if HAMMERTIME is False:
    '''We check the existing files so that we don\'t have to hammer the servers so much'''
    prepopulate()
    logger.info("Prepopulated the list")


def sureUrl(baseurl, url):
    ''' Return proper url that is complete and cross-platform 
        FIXME: This is a mess should be rewritten with parseurl
        FIXME: misses the favicon icon as we don't search through the paths fully
        default to url_wiki if no netloc can be determined from the baseurl
        ---needs support for cheatsheet url.---

    '''
    url_parts = urlparse(url)
    baseurl_parts = urlparse(baseurl)
    baseurl_netloc = baseurl_parts.netloc
    # if url_parts.netloc == '' and url_parts.scheme == '' and baseurl_netloc != '':
    #     # url_parts = url_parts._replace(netloc=baseurl_netloc, scheme=baseurl_parts.scheme)
    #     url_parts = urllib.parse.urljoin(baseurl_parts, url_parts)

    if url_parts.netloc == '':
        # url_parts.netloc = urllib.parse.urljoin(baseurl_netloc url[0] == "/" and url[1:] or url)
        # if ((baseurl_netloc != urlparse(url_wiki).netloc) and (baseurl_netloc !=
        #                                                        urlparse(url_openscadorg).netloc)):
        #     logger.warning("{} not from expected OpenSCAD domains".format(baseurl))
        # # FIXME Should maybe check that we are only in the wiki/openscad...?
        if url_parts.netloc != baseurl_netloc:
            # has no netloc, but baseurl does: join them
            url_parts = urlparse(urllib.parse.urljoin(baseurl, url))
        # else:
            # we can't arrive here
            # url_parts = url_parts._replace(netloc=baseurl_netloc)

        elif baseurl_netloc == '' and url_parts.path.startswith('/wiki') and url_parts.netloc == '':
            # we don't even know the baseurl netloc, default to url_wiki
            url_parts = url_parts._replace(netloc=urlparse(url_wiki).netloc)
        elif baseurl_netloc.startswith('//'):
            # FIXME no idea what case this case was meant to cover?
            logger.error("Hit unexpected url/baseurl")
    elif url_parts.netloc != baseurl_netloc:
        # external resource
        pass

    if url_parts.scheme == '':
        url_parts = url_parts._replace(scheme='https')

    return url_parts.geturl()


'''
All style files will be saved as style_?.css where ? is an integer.
Two kind of styles need to be handled:
1) linked_style:
        loaded by <link href="..../load.php...">
        They are handled by download_style_from_link_tag( soup_link, ind )
        whenever necessary.
2) mported_style
        loaded by a line in a style file (that could be a linked_style):
                @import url(...) screen;
        This is handled by download_imported_style( csstext, ind )
Note: Maybe a class like: StyleReader is good for this ?
'''


def handle_styles(baseurl, soup, ind):

    for link in soup.find_all('link'):

        # href = link.get('href')
        if baseurl != cheatsheet_url:
            href = sureUrl(baseurl, link.get('href'))
        else:
            href = sureUrl(baseurl, link.get('href'))

        # if not href.startswith( url_wiki ):
        #  href = os.path.join( url_wiki, href)

        if '/load.php?' in href:
            download_style_from_link_tag(baseurl, soup_link=link, ind=ind)
        elif baseurl == cheatsheet_url:
            download_style_from_link_tag(baseurl, soup_link=link, ind=ind)
        else:
            del link['href']


def download_style_from_link_tag(baseurl, soup_link, ind):
    '''
    Download/save/redirect style loaded with <link href="..../load.php...">
    '''

    link = soup_link
    ind = ind + "# "
    href = sureUrl(baseurl, link['href'])
    logger.debug("{}: Found existing: {} href".format(ind, href))
    if href:

        # if href.startswith('//'):
        #    href = 'https:' + href

        try:
            (stylename, redirect_path) = download_style(baseurl, url=href, ind=ind)
            # NOTE: the redirect_path return by download_style needs to be
            # prepended with a "styles". This is different from the
            # case of download_imported_style
            redirect_path = os.path.join("styles", redirect_path)

            logger.debug("Redirect link's style path to: " + redirect_path)
            link['href'] = redirect_path
        except urllib.error.HTTPError:
            pass



def download_imported_style(baseurl, csstext, ind):
    '''
    Download/save style that is originally imported by a css file. The url
                in the "@import url(...)" is redirected to saved file. Return modified csstext.
    '''

    # It turns out that the only css file having imports is with a <link>:
    ##
    # https://en.wikibooks.org/w/load.php?debug=false&lang=en&modules=site&only=styles&skin=vector&*
    ##
    # Its css file contains several lines like this:
    ##
    # @import url(//en.wikibooks.org/w/index.php?title=MediaWiki:Common.css/Autocount.css&action=raw&ctype=text/css) screen;
    ##
    # We will extract the url in all @import and save them as style_?.css

    lines = csstext.split(';')
    for i, ln in enumerate(lines):

        if ln.startswith('@import'):

            logger.debug("{}: @import css line found at line #{}".format(ind, i))
            ln = ln.split('(')
            ln = [ln[0], ln[1].split(')')[0], ln[1].split(')')[1]]
            url = 'https:' + ln[1]
            (stylename, redirect_path) = download_style(baseurl, url, ind)

            logger.debug("Redirect imported style to " + redirect_path)
            lines[i] = ln[0] + '(' + redirect_path + ')' + ln[-1]

        return ';\n'.join(lines)

def download_style(baseurl, url, ind):
    '''
    Download style and update styles buffer. Return (style filename, redirect_path)
    '''

    #    if not url.startswith( url_wiki ):
    #      print(ind + ':: url not starts with url_wiki("%s"), changing it...'%url_wiki)
    #      url = urllib.parse.urljoin( url_wiki, url[0]=="/" and url[1:] or url)
    #      print(ind + ':: New url = '+ url[:20] + '...')
    url = sureUrl(baseurl, url)

    if url in styles:
        i = styles.index(url)
        stylename = "style_%s.css" % i
        logger.debug("{} already downloaded as {}".format(url, stylename))

    else:
        i = len(styles)

        # IMPORTANT: append to styles right after i is retrieved
        styles.append(url)

        stylename = "style_%s.css" % i
        logger.info("Downloading style {} as {}".format(url, stylename))

        try:
            response = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            logger.warning(e)
            logger.warning("Missing style: {}".format(url))
            raise e

        # styletext = response.read().decode()
        try:
            styletext = response.read().decode(response.headers.get_content_charset())
            styletext = download_imported_style(baseurl, styletext, ind)
            save_style(stylename, styletext, ind)
        except TypeError:
            # No content_charset
            logger.warning("Treating link as 'style': saving {} to {}".format(url, stylename))
            path = os.path.join(dir_docs, dir_styles, stylename)
            blob = response.read()
            save_blob(path, blob)

    redirect_path = os.path.join('.', stylename)
    return (stylename, redirect_path)


def save_blob(path, blob):
    logger.debug("Saving blob to: {}".format(path))
    try:
        open(path, "xb").write(blob)
    except FileExistsError:
        logger.error("File exists! Overwriting!! {}".format(path))
        open(path, "wb").write(blob)
    except OSError as exc:
        if exc.errno == errno.ENAMETOOLONG:
            logger.error("Filename too long! Ignoring {}".format(path))

        else:
            raise  # re-raise previously caught exception

def save_style(stylename, styletext, ind):
    '''
    Called by download_style()
    '''
    path = os.path.join(dir_docs, dir_styles, stylename)
    logger.debug("{}: Saving style to: {}".format(ind, path))
    try:
        open(path, "x").write(styletext)
    except FileExistsError:
        logger.warning("File exists! appending {}".format(path))
        open(path, "w+").write(styletext)
    except OSError as exc:
        if exc.errno == errno.ENAMETOOLONG:
            logger.error("Filename too long! Ignoring {}".format(path))

        else:
            raise  # re-raise previously caught exception


def append_style(soup, local_style_path, ind):
    '''
    Append the style pointed to by local_style_path to soup.head
    '''
    # NOTE: as of 2015.07.14, this function is no longer needed.
    # But we keep it here for future reference
    ##
    # Note that bs('<link...>') will auto add stuff to make it a
    # well formed html doc so we will have to peel an extra layer:
    ##
    # >>> link = bs('<link ...>')
    # >>> link
    # <html><head><link .../></head></html>
    ##
    # This is parser dependent: bs('<link ...>', parser_name)

    linkdoc = bs('<link rel="stylesheet" type="text/css" href="%s">' %
                 local_style_path)
    link = linkdoc.head.link
    logger.debug("Appending link to soup.head: {} ".format(link))
    soup.head.append(link)


def handle_scripts(soup, ind):
    '''
    All scripts are shutdown and deleted if possible
    '''


    for s in soup.findAll("script"):

        logger.debug("{}: Clearing script: {}".format(ind, str(s)))
        s.clear()
        try:
            del s['src']
        except:
            pass
        logger.debug("Cleared script.")


# ========================================================
##
# tag <a...> (Note: imgs are handled within <a>)
##
# Go thru each <a>, load page or img as needed
# ========================================================


def handle_tagAs(baseurl, soup, ind):

    # print(ind + '>>> handle_tagAs(soup)')
    for a in soup.find_all('a'):
        href = a.get('href')
        '''
        href could be:
        https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/First_Steps
        https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/First_Steps/Creating_a_simple_model

        But we save all pages in the folder where the home page is anyway.
        '''

        if a.string == 'edit':  # Remove [<a...>edit</a>]
            a.findParents()[0].clear()

        if href:
            href_parts = urlparse(href)
            # if href_parts.netloc == url_wiki and href_parts.path.startswith(url_openscadwiki):
            # if href.startswith(url_wiki + url_openscadwiki):
            #     href = href[len(url_wiki):]

            # Note we compare with the the WIKIPATH and the openscadorg NETLOC
            starts_with_wiki = href_parts.path.startswith(urlparse(url_openscadwiki).path)
            starts_with_openscadorg = (href_parts.netloc == urlparse(url_openscadorg).netloc)
            if (starts_with_wiki or starts_with_openscadorg):

                # like: aaa#bbb=> [aaa,bbb]
                fnames = href.split("/")[-1].split("#")  # like: aaa#bbb=> [aaa,bbb]
                fname  = fnames[0] + ".html"
                fnamebranch = fname + (len(fnames) > 1 and ("#" + fnames[1]) or "")

                if not fname == 'Print_version.html':

                    handle_page(url=href, indent=len(ind))
                    a['href'] = fnamebranch
                    logger.info("{}: Pages: {} -  handle_tagAs saving page {}. New href = {}".format(ind, len(pages), os.path.join(dir_docs, fname), a.get('href')))

            # hopefully already covered in sameUrl
            # elif href_parts.path.startswith('/wiki'):
            #     a['href'] = url_wiki + href
            elif href.startswith('//'):
                a['href'] = 'https:' + href

            if a.img and not a.img['src'].startswith('/static/images'):
                # FIXME should do better inspection of the links to handle svg
# All imgs are wrapped inside <a>, so download_img() is called when handling <a> (handle_tagAs)

                try:
                    imgname = download_img(baseurl, soup_a=a, ind=ind)
                    redirect_img(a, imgname, ind)
                except urllib.error.HTTPError:
                    pass
                except OSError as exc:
                    if exc.errno == errno.ENAMETOOLONG:
                        logger.error("Unable to save the image. ignoring")
                    else:
                        raise
    return soup


def download_img(baseurl, soup_a, ind):
    '''
    Download an image in <a...><img ...></a>. Return imgname
                soup_a: a BeautifulSoup tag class
                ind   : indent for logger
    '''

    # print(ind + '>>> download_img(soup_a)')
    src = sureUrl(baseurl, soup_a.img['src'])
    #    if src.startswith('//'):
    #       src = "https:" + src
    #    elif not src.startswith( url_wiki):
    #      src = urllib.parse.urljoin( url_wiki, src)

    imgname = src.split("/")[-1]

    # Decode url:
    #  Some img name contains %28,%29 for "(",")", resp, and %25 for %.
    imgname = imgname.replace('%28', '(').replace('%29', ')').replace('%25', '%')

    logger.debug("{}:  Img src: {}".format(ind, src))

    savepath = os.path.join(dir_imgs, imgname)  # local img path
    if savepath not in imgs:

        logger.info("Downloading image: " + imgname)
        try:
            try:
                with open(savepath, 'x'):
                    pass
            except FileExistsError:
                logger.error("File exists, Overwriting... {}".format(savepath))

            urllib.request.urlretrieve(src, savepath)  # download image
            imgs.append(savepath)
            logger.debug(ind + "Saved img as: " + savepath)
        except urllib.error.HTTPError as e:
            logger.warning("404 image: {}".format(src))
            raise e
        except OSError as exc:
            if exc.errno == errno.ENAMETOOLONG:
                logger.error("Filename too long! Ignoring... {}".format(imgname))
                imgs.append(savepath) # no point in retrying later on either
            # TODO 
            # this currently occurs due to the build notification icon etc actually being a link to
            # an svg file hosted on github - at least on my machine ... ?
            else:
                raise  # re-raise previously caught exception


# Remove srcset that seems to cause problem in some Firefox
    del soup_a.img['srcset']

    # For debug:
    # print(ind+ "a.img: "+str(a))

    return imgname


def redirect_img(soup_a, imgname, ind):
    '''
    Redirect img src links in soup_a (<a...><img ...></a>) to local path.

                soup_a: a BeautifulSoup tag class
                ind   : indent for logger
    '''
    linkurl = os.path.join('.', 'imgs', imgname)  # ./imgs/img.png
    logger.debug("Img links redirect to: " + linkurl)
    soup_a.img['src'] = linkurl
    soup_a['href'] = linkurl
    logger.debug("Total imgs: " + str(len(imgs)))

    # For debug:
    # print(ind+ "a.img: "+str(a))


# ========================================================
##
# misc
##
# ========================================================


def getFooterSoup(pageurl, pagename):
    '''
    Return a BeautifulSoup tag as a footer soup
    '''
    A = '<a style="color:black" href="%s">%s</a>'

    A_page = A % (pageurl.split("#")[0], pagename.split(".")[0])
    A_license = A % ("http://creativecommons.org/licenses/by-sa/3.0/",
                     "Creative Commons Attribution-Share-Alike License 3.0")
    A_offliner = A % (url_offliner, "openscad_offliner")

    footer = ('''<div style="font-size:13px;color:darkgray;text-align:center">
        Content of this page is extracted on %(date)s from the online OpenSCAD
                Wikipedia article %(page)s (released under the %(license)s)
                using %(offliner)s
                </div>''') % {
        "page": A_page,
        "license": A_license,
        "offliner": A_offliner,
        "date": (time.strftime("%Y/%m/%d %H:%M"))
    }

    return bs(footer)


def removeNonOpenSCAD(soup, url):
    '''
    Given the whole soup, remove non OpenSCAD parts
    '''
    for elm in soup.findAll("noscript"):
        elm.clear()

    unwanted_div_classes = ["printfooter", "catlinks", "noprint"]
    unwanted_table_classes = ['noprint', 'ambox']

    for kls in unwanted_div_classes:
        for elm in soup.findAll('div', kls):
            elm['style'] = "display:none"
            elm.clear()
        for kls in unwanted_table_classes:
            for elm in soup.findAll('table', kls):
                elm.clear()
                elm['style'] = "display:none"

        # Get rid of wiki menu and structure
        content = soup.find(id='page-content')  # Content didn't exist in one case
        if content is None:
            # TODO maybe it still does somewhere else though?  should remove
            content = soup.find(id='content')

        try:
            content['style'] = "margin-left:0px"
            soup.body.clear()
            soup.body.append(content)
        except TypeError:
            logger.error("no 'content/page-content' in {} found".format(url))
        # soup.body.clear() # FIXME maybe we shouldn't destroy everything based on this test...


# ========================================================
##
# html page --- this is the main function
##
# ========================================================


def handle_page(url, folder=dir_docs, indent=0):

    # For logger
    ind = '[' + str(len(pages) + 1) + '] '
    indm = ind + "| "  # for image

    logger.debug("{} handle_page(url='{}', folder='{}')".format(ind, url, folder))
    # print ind+ 'Page: ' + href

    parts = urllib.parse.urlparse(url)
    baseurl = parts.netloc
    url = sureUrl(baseurl, url)

    if url not in pages:  # url not already downloaded

        logger.info("Downloading: {} load to Page # {}".format(url, len(pages) + 1))

        try:
            response = urllib.request.urlopen(url)

            html = response.read()
            pages.append(url)

            soup = bs(html, 'html.parser')
            handle_styles(url, soup, ind)
            soup = handle_tagAs(url, soup, ind)
            handle_scripts(soup, ind)

            if url != cheatsheet_url:
                removeNonOpenSCAD(soup, url)

            fname = url.split("/")[-1].split("#")[0] + ".html"
            soup.body.append(getFooterSoup(url, fname))

            # Save
            filepath = os.path.join(folder, fname)
            logger.debug(ind + "Saving: ", filepath)
            try:
                open(filepath, "x").write(str(soup))
            except FileExistsError:
                logger.error("File exists! Overwriting!! {}".format(filepath))
                open(filepath, "w").write(str(soup))
            logger.debug(ind + "{} of pages: {} of styles: {} of imgs: ".format(len(pages),
                                                                                len(styles),
                                                                                len(imgs)))
        # '''# for debugging
        # if len(pages)==94:
        #     for s in styles:
        #         print()
        #         print()
        #         print(s)
        # '''
        except urllib.error.HTTPError:
            logger.error("404: {}".format(url))


handle_page(url=cheatsheet_url)
populate()
