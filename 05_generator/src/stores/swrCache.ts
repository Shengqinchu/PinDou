import { defineStore } from 'pinia';

import { getArtworkDetail, getArtworkGallery } from '../api';
import type { Artwork, ArtworkListResponse } from '../api/types';

const GALLERY_STALE_TIME_MS = 60_000;
const GALLERY_MAX_AGE_MS = 10 * 60_000;
const GALLERY_CACHE_LIMIT = 12;
const ARTWORK_CACHE_LIMIT = 20;

interface CacheEntry<T> {
  data: T;
  updatedAt: number;
}

interface Snapshot<T> {
  data: T;
  isFresh: boolean;
  updatedAt: number;
}

const galleryRequests = new Map<string, Promise<ArtworkListResponse>>();
const artworkRequests = new Map<string, Promise<Artwork>>();

function galleryKey(page: number, size: number): string {
  return `${page}:${size}`;
}

function cacheAge(updatedAt: number): number {
  return Date.now() - updatedAt;
}

function isGalleryFresh(updatedAt: number): boolean {
  return cacheAge(updatedAt) < GALLERY_STALE_TIME_MS;
}

function isGalleryUsable(updatedAt: number): boolean {
  return cacheAge(updatedAt) < GALLERY_MAX_AGE_MS;
}

export const useSWRCacheStore = defineStore('swrCache', {
  state: () => ({
    gallery: {} as Record<string, CacheEntry<ArtworkListResponse>>,
    galleryOrder: [] as string[],
    galleryEpoch: 0,
    artworks: {} as Record<string, CacheEntry<Artwork>>,
    artworkOrder: [] as string[]
  }),
  actions: {
    getGallerySnapshot(page: number, size: number): Snapshot<ArtworkListResponse> | null {
      const key = galleryKey(page, size);
      const entry = this.gallery[key];
      if (!entry) {
        return null;
      }
      if (!isGalleryUsable(entry.updatedAt)) {
        this.dropGalleryKey(key);
        return null;
      }
      this.touchGalleryKey(key);
      return {
        data: entry.data,
        isFresh: isGalleryFresh(entry.updatedAt),
        updatedAt: entry.updatedAt
      };
    },
    async fetchGallery(page: number, size: number, force = false): Promise<ArtworkListResponse> {
      const key = galleryKey(page, size);
      if (!force) {
        const snapshot = this.getGallerySnapshot(page, size);
        if (snapshot) {
          return snapshot.data;
        }
      }

      const inflight = galleryRequests.get(key);
      if (inflight) {
        return inflight;
      }

      const requestEpoch = this.galleryEpoch;
      const request = getArtworkGallery(page, size)
        .then((response) => {
          if (this.galleryEpoch === requestEpoch) {
            this.setGallery(key, response);
          }
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
      this.galleryEpoch += 1;
      this.gallery = {};
      this.galleryOrder = [];
      galleryRequests.clear();
    },
    getArtworkSnapshot(artworkId: string): Snapshot<Artwork> | null {
      const entry = this.artworks[artworkId];
      if (!entry) {
        return null;
      }
      this.touchArtworkKey(artworkId);
      return { data: entry.data, isFresh: true, updatedAt: entry.updatedAt };
    },
    async fetchArtwork(artworkId: string, force = false): Promise<Artwork> {
      if (!force) {
        const snapshot = this.getArtworkSnapshot(artworkId);
        if (snapshot) {
          return snapshot.data;
        }
      }

      const inflight = artworkRequests.get(artworkId);
      if (inflight) {
        return inflight;
      }

      const requestEpoch = this.galleryEpoch;
      const request = getArtworkDetail(artworkId)
        .then((artwork) => {
          if (this.galleryEpoch === requestEpoch) this.setArtwork(artwork);
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
      this.touchArtworkKey(artwork.artwork_id);
    },
    invalidateArtwork(artworkId: string): void {
      this.dropArtworkKey(artworkId);
      artworkRequests.delete(artworkId);
    },
    clearAll(): void {
      this.galleryEpoch += 1;
      this.gallery = {};
      this.galleryOrder = [];
      this.artworks = {};
      this.artworkOrder = [];
      galleryRequests.clear();
      artworkRequests.clear();
    },
    setGallery(key: string, data: ArtworkListResponse): void {
      this.gallery[key] = { data, updatedAt: Date.now() };
      this.touchGalleryKey(key);
    },
    touchGalleryKey(key: string): void {
      this.galleryOrder = this.galleryOrder.filter((item) => item !== key);
      this.galleryOrder.push(key);
      while (this.galleryOrder.length > GALLERY_CACHE_LIMIT) {
        const staleKey = this.galleryOrder.shift();
        if (staleKey) {
          delete this.gallery[staleKey];
          galleryRequests.delete(staleKey);
        }
      }
    },
    dropGalleryKey(key: string): void {
      delete this.gallery[key];
      this.galleryOrder = this.galleryOrder.filter((item) => item !== key);
      galleryRequests.delete(key);
    },
    touchArtworkKey(artworkId: string): void {
      this.artworkOrder = this.artworkOrder.filter((item) => item !== artworkId);
      this.artworkOrder.push(artworkId);
      while (this.artworkOrder.length > ARTWORK_CACHE_LIMIT) {
        const staleArtworkId = this.artworkOrder.shift();
        if (staleArtworkId) {
          delete this.artworks[staleArtworkId];
          artworkRequests.delete(staleArtworkId);
        }
      }
    },
    dropArtworkKey(artworkId: string): void {
      delete this.artworks[artworkId];
      this.artworkOrder = this.artworkOrder.filter((item) => item !== artworkId);
      artworkRequests.delete(artworkId);
    }
  }
});
