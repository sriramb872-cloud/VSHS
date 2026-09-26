// frontend/src/components/EditModal.tsx
import React, { useState } from 'react';

export interface Field {
  key: string;
  label: string;
  type?: 'text' | 'email' | 'tel' | 'date' | 'datetime-local' | 'select' | 'textarea' | 'password';
  options?: { value: string | number; label: string }[]; // for type: 'select'
  required?: boolean;
}

interface EditModalProps {
  title: string;
  fields: Field[];
  initialValues: Record<string, any>;
  onSubmit: (values: Record<string, any>) => Promise<void>;
  onClose: () => void;
}

export const EditModal: React.FC<EditModalProps> = ({ title, fields, initialValues, onSubmit, onClose }) => {
  const [values, setValues] = useState<Record<string, any>>(initialValues);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit(values);
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <form
        onClick={e => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="bg-white rounded-2xl p-5 w-full max-w-md space-y-3 shadow-xl max-h-[90vh] overflow-y-auto"
      >
        <h2 className="text-sm font-bold text-slate-900">{title}</h2>
        {fields.map(f => (
          <div key={f.key} className="space-y-1">
            <label className="text-xs font-semibold text-slate-600">{f.label}</label>
            {f.type === 'select' ? (
              <select
                className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                value={values[f.key] ?? ''}
                required={f.required}
                onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}
              >
                <option value="" disabled>Select...</option>
                {f.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            ) : f.type === 'textarea' ? (
              <textarea
                className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                value={values[f.key] ?? ''}
                required={f.required}
                onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}
              />
            ) : (
              <input
                type={f.type || 'text'}
                className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                value={values[f.key] ?? ''}
                required={f.required}
                onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}
              />
            )}
          </div>
        ))}
        {error && <p className="text-xs text-rose-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="text-xs px-3 py-2 rounded-lg border border-slate-200">Cancel</button>
          <button type="submit" disabled={saving} className="text-xs px-3 py-2 rounded-lg bg-indigo-600 text-white font-bold disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  );
};

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  confirmVariant?: 'danger' | 'primary';
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  title,
  message,
  confirmLabel = 'Confirm',
  confirmVariant = 'danger',
  onConfirm,
  onClose,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Operation failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        onClick={e => e.stopPropagation()}
        className="bg-white rounded-2xl p-5 w-full max-w-sm space-y-3 shadow-xl"
      >
        <h2 className="text-sm font-bold text-slate-900">{title}</h2>
        <p className="text-xs text-slate-600">{message}</p>
        {error && <p className="text-xs text-rose-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="text-xs px-3 py-2 rounded-lg border border-slate-200"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={handleConfirm}
            className={`text-xs px-3 py-2 rounded-lg font-bold text-white disabled:opacity-50 ${
              confirmVariant === 'danger' ? 'bg-rose-600 hover:bg-rose-700' : 'bg-indigo-600 hover:bg-indigo-700'
            }`}
          >
            {submitting ? 'Processing…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditModal;
