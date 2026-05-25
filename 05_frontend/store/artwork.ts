import { defineStore } from 'pinia';
import { api, Artwork, SizePreset, StylePreset, PatternSheet, PreviewResult } from '../api';

export const useArtworkStore = defineStore('artwork', {
  state: () => ({
    artworks: [] as Artwork[],
    currentArtwork: null as Artwork | null,
    currentPreview: null as PreviewResult | null,
    currentPattern: null as PatternSheet | null,
  }),
  actions: {
    async fetchArtworks() {
      try {
        const list = await api.getArtworks();
        this.artworks = list;
        return list;
      } catch (error) {
        console.error('Fetch artworks error:', error);
        throw error;
      }
    },
    async fetchArtworkDetail(id: string) {
      try {
        const detail = await api.getArtworkDetail(id);
        this.currentArtwork = detail;
        this.currentPattern = detail.pattern_data;
        return detail;
      } catch (error) {
        console.error('Fetch artwork detail error:', error);
        throw error;
      }
    },
    async generateAIPreview(filePath: string, style: StylePreset, size: SizePreset) {
      try {
        const preview = await api.generatePreview(filePath, style, size);
        this.currentPreview = preview;
        return preview;
      } catch (error) {
        console.error('Generate AI preview error:', error);
        throw error;
      }
    },
    async buildPatternSheet(params: {
      size: SizePreset;
      preview_id?: string;
      rawImageFilePath?: string;
      mode: 'auto' | 'script' | 'ai';
    }) {
      try {
        const sheet = await api.buildPattern(params);
        this.currentPattern = sheet;
        return sheet;
      } catch (error) {
        console.error('Build pattern sheet error:', error);
        throw error;
      }
    },
    async deleteArtwork(id: string) {
      try {
        const res = await api.deleteArtwork(id);
        if (res.success) {
          this.artworks = this.artworks.filter(art => art.artwork_id !== id);
        }
        return res;
      } catch (error) {
        console.error('Delete artwork error:', error);
        throw error;
      }
    }
  }
});
