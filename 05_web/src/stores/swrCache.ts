import { defineStore } from 'pinia';

import { getArtworkDetail, getArtworkGallery } from '../api';
import type { Artwork, ArtworkListResponse } from '../api/types';

const STALE_TIME_MS = 60_000;

interface CacheEntry<T> {
  data: T;
  updatedAt: number;
}

interface Snapshot<T> {
  data: T;
  isFresh: boolean;
}

const galleryRequests = new Map<string, Promise<ArtworkListResponse>>();
const artworkRequests = new Map<string, Promise<Artwork>>();

function galleryKey(page: number, size: number): string {
  return `${page}:${size}`;
}

function isFresh(updatedAt: number): boolean {
  return Date.now() - updatedAt < STALE_TIME_MS;
}

export const useSWRCacheStore = defineStore('swrCache', {
  state: () => ({
    gallery: {} as Record<string, CacheEntry<ArtworkListResponse>>,
    artworks: {} as Record<string, CacheEntry<Artwork>>
  }),
  actions: {
    getGallerySnapshot(page: number, size: number): Snapshot<ArtworkListResponse> | null {
      const entry = this.gallery[galleryKey(page, size)];
      return entry ? { data: entry.data, isFresh: isFresh(entry.updatedAt) } : null;
    },
    async fetchGallery(page: number, size: number, force = false): Promise<ArtworkListResponse> {
      const key = galleryKey(page, size);
      const entry = this.gallery[key];
      if (!force && entry && isFresh(entry.updatedAt)) {
        return entry.data;
      }

      const inflight = galleryRequests.get(key);
      if (inflight) {
        return inflight;
      }

      const request = getArtworkGallery(page, size)
        .then((response) => {
          this.gallery[key] = { data: response, updatedAt: Date.now() };
          return response;
        })
        .finally(() => {
          galleryRequests.delete(key);
        });
      galleryRequests.set(key, request);
      return request;
    },
    async revalidateGallery(page: number, size: number): Promise<ArtworkListResponse> {
      return this.fetchGallery(page, size, true);
    },
    invalidateGallery(): void {
      this.gallery = {};
      galleryRequests.clear();
    },
    getArtworkSnapshot(artworkId: string): Snapshot<Artwork> | null {
      const entry = this.artworks[artworkId];
      return entry ? { data: entry.data, isFresh: isFresh(entry.updatedAt) } : null;
    },
    async fetchArtwork(artworkId: string, force = false): Promise<Artwork> {
      const entry = this.artworks[artworkId];
      if (!force && entry && isFresh(entry.updatedAt)) {
        return entry.data;
      }

      const inflight = artworkRequests.get(artworkId);
      if (inflight) {
        return inflight;
      }

      const request = getArtworkDetail(artworkId)
        .then((artwork) => {
          this.setArtwork(artwork);
          return artwork;
        })
        .finally(() => {
          artworkRequests.delete(artworkId);
        });
      artworkRequests.set(artworkId, request);
      return request;
    },
    async revalidateArtwork(artworkId: string): Promise<Artwork> {
      return this.fetchArtwork(artworkId, true);
    },
    setArtwork(artwork: Artwork): void {
      this.artworks[artwork.artwork_id] = { data: artwork, updatedAt: Date.now() };
    },
    invalidateArtwork(artworkId: string): void {
      delete this.artworks[artworkId];
      artworkRequests.delete(artworkId);
    },
    clearAll(): void {
      this.gallery = {};
      this.artworks = {};
      galleryRequests.clear();
      artworkRequests.clear();
    }
  }
});
