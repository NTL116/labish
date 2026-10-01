import CreativeGallery from "@/components/creative-gallery";
import { photographs } from "@/data/photographs";

export default function PhotographyPage() {
  const items = photographs.map((photograph) => ({
    slug: photograph.slug,
    title: photograph.title,
    creator: photograph.artist,
    image: photograph.image,
    alt: photograph.alt,
  }));

  return (
    <CreativeGallery title="Photography" collection="photography" items={items} />
  );
}