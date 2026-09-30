import CreativeGallery from "@/components/creative-gallery";
import { artworks } from "@/data/artworks";

export default function FineArtPage() {
  const items = artworks.map((artwork) => ({
    slug: artwork.slug,
    title: artwork.title,
    creator: artwork.artist,
    image: artwork.image,
    alt: artwork.alt,
  }));

  return (
    <CreativeGallery title="Fine Art" collection="art" items={items} />
  );
}