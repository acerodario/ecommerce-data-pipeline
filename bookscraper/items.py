import scrapy


class BookItem(scrapy.Item):
    upc = scrapy.Field()
    title = scrapy.Field()
    price = scrapy.Field()
    stock = scrapy.Field()
    rating = scrapy.Field()
    category = scrapy.Field()
    description = scrapy.Field()
    image_url = scrapy.Field()
    url = scrapy.Field()
