// src/services/search.ts
import api from './api';
import { GlobalSearchResults } from '../types/search';

export const searchService = {
  /**
   * Global search. Results are scoped server-side by the caller's role and
   * tenant, so no client-side filtering is applied (or wanted).
   */
  async globalSearch(params: { q: string; school_id?: number; limit?: number }): Promise<GlobalSearchResults> {
    const response = await api.get<GlobalSearchResults>('/search', { params });
    return response.data;
  },
};

export default searchService;
