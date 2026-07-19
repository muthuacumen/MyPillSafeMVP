import client from './client';

export interface InstructionRequest {
  drug_name: string;
  dosage: string | null;
  frequency_type: string;
  specific_times: string[];
  with_food: boolean;
  purpose: string | null;
  max_daily_dose: number | null;
  language: string;
}

export interface InstructionResponse {
  message: string;
  language: string;
}

export const instructionsApi = {
  getMessage: (payload: InstructionRequest) =>
    client.post<InstructionResponse>('/instructions/message', payload),
};
