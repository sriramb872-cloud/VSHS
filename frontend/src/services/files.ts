// src/services/files.ts
import api from './api';

export interface UploadedFile {
  photo_url: string;
  file_id: number;
  file_size: number;
  content_type: string;
  message: string;
}

export interface FileMetadata {
  id: number;
  filename: string;
  original_filename: string;
  file_path: string;
  content_type: string;
  file_size: number;
  entity_type?: string | null;
  entity_id?: string | null;
  uploaded_by_id?: number | null;
  school_id?: number | null;
  created_at?: string | null;
  exists_on_disk?: boolean;
}

export const filesService = {
  /**
   * Upload a profile photo. The server validates that the bytes really are a
   * jpg/png/webp image of at most 5 MB and rejects anything else with 400/413.
   */
  async uploadProfilePhoto(file: File): Promise<UploadedFile> {
    const form = new FormData();
    form.append('file', file);
    const response = await api.post<UploadedFile>('/files/profile-photo', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async getMetadata(fileId: number): Promise<FileMetadata> {
    const response = await api.get<FileMetadata>(`/files/metadata/${fileId}`);
    return response.data;
  },
  async listMetadata(params?: { entity_type?: string; entity_id?: string; limit?: number }): Promise<FileMetadata[]> {
    const response = await api.get<FileMetadata[]>('/files/metadata', { params });
    return response.data;
  },

  /** Clear the caller's profile photo pointer. */
  async deleteProfilePhoto(): Promise<{ message: string; profile_photo: null }> {
    const response = await api.delete<{ message: string; profile_photo: null }>('/files/profile-photo');
    return response.data;
  },
};

export default filesService;
