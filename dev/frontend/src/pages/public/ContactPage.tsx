import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Mail, Send } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { contactApi } from '@/api/contact';

const schema = z.object({
  full_name: z.string().min(1, 'Full name is required'),
  email: z.string().email('Enter a valid email'),
  message: z.string().min(1, 'Message is required'),
});
type FormData = z.infer<typeof schema>;

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setError('');
    try {
      await contactApi.submit(data);
      setSubmitted(true);
      reset();
    } catch {
      setError('Could not send your message. Please try again later.');
    }
  };

  return (
    <div className="max-w-xl mx-auto px-6 py-12">
      <div className="text-center mb-8">
        <div className="h-14 w-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4">
          <Mail className="h-7 w-7 text-teal-600" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Contact Us</h1>
        <p className="text-slate-500 mt-2">Questions, feedback, or accessibility concerns — we&apos;d like to hear from you.</p>
      </div>

      <Card>
        {submitted && <div className="mb-4"><Alert variant="success" message="Thank you — we received your message and will respond soon." /></div>}
        {error && <div className="mb-4"><Alert variant="error" message={error} /></div>}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input label="Full name" error={errors.full_name?.message} {...register('full_name')} />
          <Input label="Email address" type="email" error={errors.email?.message} {...register('email')} />
          <div>
            <label className="label" htmlFor="message">Message</label>
            <textarea
              id="message"
              rows={5}
              className={`input-field ${errors.message ? 'input-error' : ''}`}
              {...register('message')}
            />
            {errors.message && <p className="mt-1.5 text-xs text-danger-text">{errors.message.message}</p>}
          </div>
          <Button type="submit" loading={isSubmitting} className="w-full" size="lg">
            <Send className="h-4 w-4" /> Send Message
          </Button>
        </form>
      </Card>
    </div>
  );
}
