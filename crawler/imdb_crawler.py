"""
The IMDB movie database crawler
"""
import urllib.request
import re
import json

import bs4


class IMDBMovieCrawler:
    """The crawler to get single movie data"""

    def __init__(self, conf, imdb_id=None):
        self.conf = conf
        self.base_url = conf['base_url']
        if not self.base_url.endswith('/'):
            self.base_url += '/'

        # for many imdb_ids usage
        if imdb_id is not None:
            self.set_imdb_id(imdb_id)

    def set_imdb_id(self, imdb_id):
        """set movie's imdbId when changing a movie"""
        self.imdb_id = imdb_id
        self.movie_url = self.base_url + 'tt' + self.imdb_id + '/'

    def get_imdb_id(self):
        """get current movie's imdbId"""
        return self.imdb_id

    def get_movie_data(self):
        """main method to get movie data"""
        movie_data = self._get_movie_category(self.conf['category'])
        return movie_data

    def _get_movie_category(self, category_conf):
        category_data = dict()
        for c_conf in category_conf:
            if not c_conf.get('enabled', True):
                continue
            category_name = c_conf['name']
            category_data[category_name] = self._get_category_page(c_conf['pages'])

        return category_data

    def _get_category_page(self, page_conf):
        page_data = dict()
        for p_conf in page_conf:
            if not p_conf.get('enabled', True):
                continue
            p_name = p_conf['name']
            p_param = p_conf['param']

            p_url = self.movie_url + p_param
            p_html = urllib.request.urlopen(p_url).read().decode('UTF-8')
            p_soup = bs4.BeautifulSoup(p_html, 'html5lib')

            page_data[p_name] = self._get_page_object(p_soup, p_conf['object'])

        return page_data

    def _get_page_object(self, soup, object_conf):
        object_data = dict()
        for obj_conf in object_conf:
            if not obj_conf.get('enabled', True):
                continue
            o_name = obj_conf['name']
            o_param = obj_conf.get('param', None)
            o_parse = obj_conf.get('parse', True)
            o_object = obj_conf.get('object', None)
            o_index = obj_conf.get('index', 0)
            o_standard = obj_conf.get('standard', None)
            o_type = obj_conf.get('type', 'text')

            if not o_parse and o_object is None:
                continue

            if o_param is not None:
                objs = self._get_object_by_param(soup, o_param)
                objs = self._get_object_by_index(o_index, objs)
                if o_parse:
                    o_content = [self._get_object_content(obj, o_type) for obj in objs]
                    if o_standard is not None:
                        o_content = [
                            self._get_standard_object_content(
                                content,
                                o_standard
                            ) for content in o_content
                        ]
            elif obj_conf.get('index', None) is not None:
                objs = self._get_object_by_index(o_index, soup)

            if o_object is not None:
                o_child = list()
                if o_param is not None:
                    for obj in objs:
                        o_child.append(self._get_page_object(obj, o_object))
                else:
                    o_child.append(self._get_page_object(soup, o_object))

            object_data[o_name] = dict()
            if o_parse:
                if o_object is not None:
                    object_data[o_name]['value'] = o_content
                    object_data[o_name]['child'] = o_child
                else:
                    object_data[o_name] = o_content
            else:
                object_data[o_name] = o_child

        return object_data

    def _get_object_by_param(self, soup, param):
        if isinstance(param, str):
            return soup.select(param)
        elif isinstance(param, dict):
            param_real = param['param']
            param_index = param['index']
            child_param = param['child-param']

            object_real = soup.select(param_real)[param_index]
            if isinstance(child_param, dict):
                return self._get_object_by_param(object_real, child_param)
            else:
                return object_real.select(child_param)

        return None

    def _get_object_by_index(self, index, it_):
        if isinstance(index, int):
            return [it_[index]]
        elif isinstance(index, list):
            return [it_[i] for i in index]
        elif isinstance(index, str):
            index_s_e = index.split(':')
            start = index_s_e[0]
            end = index_s_e[1]
            start = int(start) if start != '' else 0
            end = int(end) if end != '' else len(it_)
            return it_[start:end]
        elif isinstance(index, dict):
            start = index['start']
            end = index['end']
            if isinstance(start, dict):
                start = self._get_index_from_dict(start, it_)
            if isinstance(end, dict):
                end = self._get_index_from_dict(end, it_)
            if start is None:
                return []
            elif end is None:
                return it_[:]
            return it_[start:end]

        return None

    def _get_index_from_dict(self, index, it_):
        param = index['param']
        next_ = index['next']
        offset = index.get('offset', 0)
        if next_ == 'parent':
            a = it_[0].find_parent()
            b = a.select(param)
            if len(b) == 0:
                return None
            stop_index = it_.index(b[0].find_parent())
        return stop_index + offset

    def _get_object_content(self, obj, o_type):
        if o_type == 'text':
            return obj.get_text()
        elif isinstance(o_type, dict):
            o_type_real = o_type['type']
            if o_type_real == 'attr':
                o_type_attr = o_type['attr']
                return obj[o_type_attr]

        return None

    def _get_standard_object_content(self, content, standard_conf):
        if standard_conf.get('strip', True):
            content = content.strip()
        dos = standard_conf.get('do', None)
        if dos is not None:
            for do_ in dos:
                do_type = do_['type']
                if do_type == 'replace':
                    pattern = do_['pattern']
                    dest = do_['dest']
                    content = re.sub(pattern, dest, content)
        return content

    def test_get_page_object(self, html_page, category_index, page_index):
        p_conf = self.conf['category'][category_index]['pages'][page_index]['object']
        soup = bs4.BeautifulSoup(html_page, 'html5lib')
        data = self._get_page_object(soup, p_conf)
        print(data)


class IMDBCrawler:
    """The crawler to get specified movie data"""

    def __init__(self, conf, imdb_id_iter, save_path, **kwargs):
        self.conf = conf
        self.imdb_id_iter = imdb_id_iter
        self.save_path = save_path

        self.save_in_one = kwargs.get('save_in_one', True)
        self.save_in_same_dir = kwargs.get('save_in_same_dir', False)

        self.imdb_movie_crawler = IMDBMovieCrawler(self.conf)

    def crawl(self):
        """main method to get all data"""
        for i, imdb_id in enumerate(self.imdb_id_iter, 1):
            try:
                print('\r%d/%d' % (i, len(self.imdb_id_iter)), end='')
                standard_id = imdb_id.strip()
                self.imdb_movie_crawler.set_imdb_id(standard_id)
                movie_data = self.imdb_movie_crawler.get_movie_data()
                f = open(self.save_path + standard_id, 'w', encoding='UTF-8')
                json.dump(movie_data, f, indent=4)
                f.close()
            except:
                continue
