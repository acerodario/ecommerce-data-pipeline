"""Spider del catálogo completo de books.toscrape.com (sitio de práctica para scraping)."""

from __future__ import annotations

import scrapy

from bookscraper.items import BookItem
from bookscraper.normalize import clean_text, parse_price, parse_rating, parse_stock


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    def parse(self, response):
        """Página de listado: sigue cada producto y la paginación."""
        for href in response.css("article.product_pod h3 a::attr(href)").getall():
            yield response.follow(href, callback=self.parse_product)

        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_product(self, response):
        """Página de detalle: arma un BookItem ya normalizado."""
        main = response.css("div.product_main")
        info = {
            clean_text(row.css("th::text").get()): clean_text(row.css("td::text").get())
            for row in response.css("table.table-striped tr")
        }
        image = response.css("div.item.active img::attr(src)").get()

        yield BookItem(
            upc=info.get("UPC"),
            title=clean_text(main.css("h1::text").get()),
            price=parse_price(main.css("p.price_color::text").get()),
            stock=parse_stock(" ".join(main.css("p.availability::text").getall())),
            rating=parse_rating(main.css("p.star-rating::attr(class)").get()),
            category=clean_text(response.css("ul.breadcrumb li:nth-child(3) a::text").get()),
            description=clean_text(response.css("#product_description + p::text").get()),
            image_url=response.urljoin(image) if image else None,
            url=response.url,
        )
