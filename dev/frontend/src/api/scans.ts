import client from './client';
import type { ScanRecord } from '@/types';

export const scansApi = {
  listMine: () => client.get<ScanRecord[]>('/scans/me'),
};
