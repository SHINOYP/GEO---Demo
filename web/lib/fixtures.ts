// Ported verbatim from streamlit_app.py's SAMPLE_PRESETS / SAMPLE_HTML_FIXTURES.
// Python's cli.py never needs to know about these — the web app sends the raw
// HTML to `cli.py analyze <url> --html-stdin`, keeping Python ML-only.

export interface Preset {
  label: string;
  url: string;
}

export const SAMPLE_PRESETS: Preset[] = [
  { label: "Select a sample page...", url: "" },
  { label: "Apex Dental Clinic (high-quality local business)", url: "https://sample-dental-clinic.example.com" },
  { label: "Luigi's Trattoria (Italian restaurant)", url: "https://sample-italian-bistro.example.com" },
  { label: "Apex Cloud Solutions (B2B SaaS)", url: "https://sample-cloud-tech.example.com" },
  { label: "Thin Local Contractor Blog (low optimization)", url: "https://sample-basic-contractor.example.com" },
];

export const SAMPLE_HTML_FIXTURES: Record<string, string> = {
  "https://sample-dental-clinic.example.com": `
    <!DOCTYPE html><html><head><title>Apex Dental Clinic - Advanced Cosmetic & Family Dentistry</title>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Dentist","name":"Apex Dental Clinic",
     "telephone":"+1-555-234-5678","openingHours":"Mo-Fr 08:00-18:00",
     "address":{"@type":"PostalAddress","streetAddress":"123 Main St","addressLocality":"Austin","addressRegion":"TX","postalCode":"78701"},
     "aggregateRating":{"@type":"AggregateRating","ratingValue":"4.9","reviewCount":"340"}}
    </script>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
      {"@type":"Question","name":"How much does teeth whitening cost?","acceptedAnswer":{"@type":"Answer","text":"Professional in-office whitening starts at $350."}},
      {"@type":"Question","name":"Do you accept dental insurance?","acceptedAnswer":{"@type":"Answer","text":"We accept all major PPO insurance plans including Delta Dental and Cigna."}}
    ]}
    </script>
    </head><body>
    <header><nav><a href="/">Home</a> | <a href="/services">Services</a> | <a href="/contact">Contact</a></nav></header>
    <main>
      <h1>Apex Dental Clinic - Expert Oral Care in Austin, TX</h1>
      <p>Apex Dental Clinic provides comprehensive dental care with over 15 years of clinical experience. Our clinic has treated over 12,000 patients with a 98% satisfaction rate.</p>
      <h2>Comprehensive Dental Services</h2>
      <p>From routine cleanings to restorative implants, our board-certified dentists use state-of-the-art 3D imaging.</p>
      <h3>Pricing & Treatment Timeline</h3>
      <table>
        <tr><th>Treatment</th><th>Duration</th><th>Average Cost</th></tr>
        <tr><td>Checkup & Cleaning</td><td>45 minutes</td><td>$120</td></tr>
        <tr><td>Dental Implants</td><td>2 visits</td><td>$1,800</td></tr>
      </table>
      <h2>Frequently Asked Questions</h2>
      <ul>
        <li><strong>Emergency visits:</strong> Same-day emergency appointments are available daily.</li>
        <li><strong>Financing:</strong> 0% APR financing is available via CareCredit.</li>
      </ul>
      <h2>Contact & Operating Hours</h2>
      <p>Call us at <strong>(555) 234-5678</strong> or visit our office at 123 Main St, Austin, TX 78701.</p>
      <p>Hours: Monday to Friday, 8:00 AM - 6:00 PM; Saturday 9:00 AM - 2:00 PM.</p>
    </main></body></html>
    `,
  "https://sample-basic-contractor.example.com": `
    <!DOCTYPE html><html><head><title>Best Handyman Services</title></head><body>
    <h1>Welcome to our Handyman Website</h1>
    <p>We do great work. Call us today for the best prices in town. We do painting, plumbing, and fixing things around your house.</p>
    <p>No job is too big or too small! Contact us today.</p>
    </body></html>
    `,
  "https://sample-italian-bistro.example.com": `
    <!DOCTYPE html><html><head><title>Luigi's Trattoria - Authentic Italian Restaurant</title>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Restaurant","name":"Luigi's Trattoria",
     "telephone":"+1-555-312-7788","openingHours":"Tu-Su 11:00-22:00",
     "address":{"@type":"PostalAddress","streetAddress":"48 Elm Street","addressLocality":"Portland","addressRegion":"OR","postalCode":"97201"},
     "aggregateRating":{"@type":"AggregateRating","ratingValue":"4.7","reviewCount":"512"}}
    </script>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
      {"@type":"Question","name":"Do you take reservations?","acceptedAnswer":{"@type":"Answer","text":"Yes, reservations are recommended on weekends and can be made by phone or online."}},
      {"@type":"Question","name":"Is there outdoor seating?","acceptedAnswer":{"@type":"Answer","text":"Yes, we have a heated patio open year-round with seating for 30 guests."}}
    ]}
    </script>
    </head><body>
    <header><nav><a href="/">Home</a> | <a href="/menu">Menu</a> | <a href="/contact">Contact</a></nav></header>
    <main>
      <h1>Luigi's Trattoria - Family-Owned Italian Dining in Portland, OR</h1>
      <p>Luigi's Trattoria has served handmade pasta and wood-fired pizza since 1998. Our dining room seats 80 guests and our chefs import ingredients directly from Italy.</p>
      <h2>Our Menu</h2>
      <p>From classic Bolognese to seasonal risottos, every dish is prepared fresh daily using recipes passed down three generations.</p>
      <h3>Pricing & Hours</h3>
      <table>
        <tr><th>Item</th><th>Course</th><th>Price</th></tr>
        <tr><td>Spaghetti Carbonara</td><td>Entree</td><td>$18</td></tr>
        <tr><td>Margherita Pizza</td><td>Entree</td><td>$16</td></tr>
      </table>
      <h2>Frequently Asked Questions</h2>
      <ul>
        <li><strong>Private events:</strong> Our back room can be reserved for parties of up to 40.</li>
        <li><strong>Gluten-free:</strong> Gluten-free pasta is available on request.</li>
      </ul>
      <h2>Contact & Operating Hours</h2>
      <p>Call us at <strong>(555) 312-7788</strong> or visit us at 48 Elm Street, Portland, OR 97201.</p>
      <p>Hours: Tuesday to Sunday, 11:00 AM - 10:00 PM. Closed Mondays.</p>
    </main></body></html>
    `,
  "https://sample-cloud-tech.example.com": `
    <!DOCTYPE html><html><head><title>Apex Cloud Solutions - B2B Cloud Infrastructure Platform</title>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Organization","name":"Apex Cloud Solutions",
     "telephone":"+1-555-998-4420",
     "address":{"@type":"PostalAddress","streetAddress":"900 Market Ave","addressLocality":"Denver","addressRegion":"CO","postalCode":"80202"},
     "aggregateRating":{"@type":"AggregateRating","ratingValue":"4.6","reviewCount":"128"}}
    </script>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
      {"@type":"Question","name":"What is the pricing model?","acceptedAnswer":{"@type":"Answer","text":"Plans are priced per active workload per month, starting at $499/month for teams of up to 10."}},
      {"@type":"Question","name":"Do you offer a free trial?","acceptedAnswer":{"@type":"Answer","text":"Yes, a 14-day free trial is available with no credit card required."}}
    ]}
    </script>
    </head><body>
    <header><nav><a href="/">Home</a> | <a href="/pricing">Pricing</a> | <a href="/contact">Contact</a></nav></header>
    <main>
      <h1>Apex Cloud Solutions - Enterprise-Grade Infrastructure for Growing Teams</h1>
      <p>Apex Cloud Solutions provides managed Kubernetes orchestration and CI/CD pipelines trusted by over 1,200 engineering teams worldwide, with a 99.98% uptime SLA.</p>
      <h2>Platform Capabilities</h2>
      <p>Our platform automates deployment, scaling, and observability across multi-cloud environments with built-in SOC 2 compliance.</p>
      <h3>Plans & Pricing</h3>
      <table>
        <tr><th>Plan</th><th>Workloads</th><th>Monthly Price</th></tr>
        <tr><td>Starter</td><td>Up to 10</td><td>$499</td></tr>
        <tr><td>Growth</td><td>Up to 50</td><td>$1,999</td></tr>
      </table>
      <h2>Frequently Asked Questions</h2>
      <ul>
        <li><strong>Onboarding:</strong> Dedicated solutions engineers assist with migration within the first 30 days.</li>
        <li><strong>Support:</strong> 24/7 support is included on all paid plans.</li>
      </ul>
      <h2>Contact</h2>
      <p>Call us at <strong>(555) 998-4420</strong> or visit our headquarters at 900 Market Ave, Denver, CO 80202.</p>
    </main></body></html>
    `,
};

export const DEFAULT_URL = "https://en.wikipedia.org/wiki/Artificial_intelligence";
