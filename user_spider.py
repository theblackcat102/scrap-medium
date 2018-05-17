import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor
from scrapy.utils.log import configure_logging
from scrapy.item import Item, Field
from scrapy.exporters import JsonItemExporter

def serialize_price(value):
    return '$ %s' % str(value)

class MediumItem(scrapy.Item):
    url_type = scrapy.Field() #post, tag or user
    url = scrapy.Field()

class JsonPipeline(object):
    def __init__(self):
        self.file = open("books.json", 'wb')
        self.exporter = JsonItemExporter(self.file, encoding='utf-8', ensure_ascii=False)
        self.exporter.start_exporting()
 
    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.file.close()
 
    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item


class UserSpider(scrapy.Spider):
    name = 'medium'
    start_urls = ['https://medium.com']
    download_delay = 5.0
    banned_word = ['upgrade', 'about', 'm', 'u', 'membership', 'search', 'policy' ,'p', 'jobs-at-medium']
    banned_link = ['https://medium.com/about',
        'https://medium.com/membership',
        'https://medium.com/search',
        'https://medium.com/upgrade',
        'https://medium.com/',
        'https://medium.com/creators']
    def start_request(self):
        self.urls = ['https://medium.com/']
        yield scrapy.Request(url=url, callback=self.parse)


    def parse(self, response):
        """
            Parses a default response
        """
        if not isinstance(response, scrapy.http.TextResponse):
            self.crawler.stats.inc_value('non_text_response')
            return
        if response.status >= 400 and response.status <= 599:
            yield {
                'invalid': True,
                'url': response.url,
                'status': 'invalid_http_status',
                'http_status': response.status,
            }
        for href in response.css('a::attr(href)').extract():
            url = response.urljoin(href)
            if 'medium.com' in href and 'mailto' not in href:    
                yield scrapy.Request(
                    url = url,
                    callback=self.parse,
                    errback=self.errback
                )
            if url not in self.banned_link and len(href.split('/')) > 3 and href.split('/')[3] not in self.banned_word:
                yield self.save_data(href)

    def save_data(self, href):
        '''
            save each link as json
        '''
        url = href.split('?')[0]
        if url in self.banned_link:
            return

        url_type = 'user'
        link_section = href.split('/')

        if len(link_section) > 4 and link_section[3] == 'tag':
            url_type = 'tag'
        if link_section[3] == 'topic':
            url_type = 'topic'
        elif link_section[3] == 's':
            url_type = 'story'
        elif len(link_section) == 5:
            url_type = 'post'
        # medium_item = MediumItem(url_type=url_type, url=url)
        # self.json_pipeline.process_item(medium_item, self)
        return {
            'url_type':url_type,
            'url': url
        }

    def errback(self, err):
        """Handles an error"""
        return {
            'invalid': True,
            'url': err.request.url,
            'status': 'error_downloading_http_response',
            'message': str(err.value),
        }

print('loaded')
process = CrawlerProcess({
    'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
    'FEED_FORMAT': 'json',
    'FEED_URI': 'data.json',
    'COOKIES_ENABLED': False,
})
process.crawl(UserSpider)
process.start()
# configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})
# runner = CrawlerRunner()
# d = runner.crawl(UserSpider)
# d.addBoth(lambda _: reactor.stop())
# reactor.run() # the script will block here until the crawling is finished
