// src/services/principals.ts
import api from './api';
import { Principal, PrincipalUpdatePayload } from '../types';

export const principalsService = {
  async listPrincipals(params?: { skip?: number; limit?: number }): Promise<Principal[]> {
    const response = await api.get<Principal[]>('/principals', { params });
    return response.data;
  },

  async getMyPrincipalProfile(): Promise<Principal> {
    const response = await api.get<Principal>('/principals/me');
    return response.data;
  },

  async updateMyPrincipalProfile(payload: PrincipalUpdatePayload): Promise<Principal> {
    const response = await api.patch<Principal>('/principals/me', payload);
    return response.data;
  },

  async getPrincipal(id: number): Promise<Principal> {
    const response = await api.get<Principal>(`/principals/${id}`);
    return response.data;
  },

  async updatePrincipal(id: number, payload: PrincipalUpdatePayload): Promise<Principal> {
    const response = await api.patch<Principal>(`/principals/${id}`, payload);
    return response.data;
  },
};

export default principalsService;

