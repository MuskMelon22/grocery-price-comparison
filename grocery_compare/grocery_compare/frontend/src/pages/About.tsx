export default function About() {
  return (
    <article className="mx-auto max-w-2xl space-y-4 py-10 leading-relaxed">
      <h1 className="text-2xl font-bold">About GroceryCompare</h1>
      <p>
        GroceryCompare scrapes BigBasket and JioMart search pages with Selenium, parses them with BeautifulSoup,
        normalises pack sizes to price per 100 g / 100 ml, matches the same product across both stores and stores every
        price in a database so price history builds up over time.
      </p>
      <h2 className="text-lg font-semibold">Disclaimer</h2>
      <p>
        This is an educational project. Scraping may violate the stores' terms of service, so it runs at low volume and
        the data is not redistributed. Prices depend on your pincode and can be out of date. Always check the store before
        buying. When a store blocks the scraper, the app says so and shows the other store's prices only.
      </p>
      <p className="text-sm text-slate-500">Not affiliated with BigBasket or JioMart.</p>
    </article>
  );
}
