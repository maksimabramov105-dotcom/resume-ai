import UrgencyBanner from "./components/UrgencyBanner";
import Nav from "./components/Nav";
import Hero from "./components/Hero";
import HowItWorks from "./components/HowItWorks";
import TrustSection from "./components/TrustSection";
import TrackerPreview from "./components/TrackerPreview";
import Pricing from "./components/Pricing";
import CtaSection from "./components/CtaSection";
import FAQ from "./components/FAQ";
import Footer from "./components/Footer";
import ScrollTracker from "./components/ScrollTracker";

export default function HomePage() {
  return (
    <>
      <ScrollTracker />
      <UrgencyBanner />
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <TrustSection />
        <TrackerPreview />
        <Pricing />
        <CtaSection />
        <FAQ />
      </main>
      <Footer />
    </>
  );
}
