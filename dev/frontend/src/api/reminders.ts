import client from './client';

export interface ReminderMessageRequest {
  medication_name: string;
  patient_first_name: string;
  language: string;
}

export interface ReminderMessageResponse {
  message: string;
  language: string;
}

export const remindersApi = {
  getMessage: (payload: ReminderMessageRequest) =>
    client.post<ReminderMessageResponse>('/reminders/message', payload),
};
