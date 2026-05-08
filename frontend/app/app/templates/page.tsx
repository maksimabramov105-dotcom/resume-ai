'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '../components/Toast';

// ── Template data ─────────────────────────────────────────────────────────────

interface Template {
  id: string;
  name: string;
  description: string;
  popular: boolean;
  tags: string[];
}

const TEMPLATES: Template[] = [
  {
    id: 'modern-blue',
    name: 'Modern Blue',
    description: 'Clean two-column layout with blue accent headers. ATS-friendly.',
    popular: true,
    tags: ['Two-column', 'ATS', 'Corporate'],
  },
  {
    id: 'classic-serif',
    name: 'Classic Serif',
    description: 'Traditional single-column with serif typography. Timeless.',
    popular: false,
    tags: ['Single-column', 'Traditional', 'Elegant'],
  },
  {
    id: 'minimal-white',
    name: 'Minimal White',
    description: 'Ultra-clean layout with maximum whitespace. Recruiters love it.',
    popular: false,
    tags: ['Minimal', 'Clean', 'Whitespace'],
  },
  {
    id: 'creative-gradient',
    name: 'Creative Gradient',
    description: 'Bold gradient header with modern card sections.',
    popular: true,
    tags: ['Creative', 'Gradient', 'Modern'],
  },
  {
    id: 'executive-dark',
    name: 'Executive Dark',
    description: 'Dark sidebar with white content area. Premium feel.',
    popular: false,
    tags: ['Dark', 'Sidebar', 'Premium'],
  },
  {
    id: 'tech-mono',
    name: 'Tech Mono',
    description: 'Monospace typography for engineering and dev roles.',
    popular: false,
    tags: ['Tech', 'Monospace', 'Dev'],
  },
  {
    id: 'ats-safe',
    name: 'ATS Safe',
    description: 'Plain text formatting guaranteed to pass ATS parsers. Highest pass rate.',
    popular: true,
    tags: ['ATS', 'Plain', 'High pass rate'],
  },
  {
    id: 'compact-pro',
    name: 'Compact Pro',
    description: 'Fits more on one page without sacrificing readability.',
    popular: false,
    tags: ['Compact', 'Dense', 'One-page'],
  },
  {
    id: 'bold-accent',
    name: 'Bold Accent',
    description: 'Strong typography hierarchy with bold section dividers.',
    popular: false,
    tags: ['Bold', 'Typography', 'Dividers'],
  },
  {
    id: 'clean-columns',
    name: 'Clean Columns',
    description: 'Symmetrical three-column skills section with clean layout.',
    popular: false,
    tags: ['Three-column', 'Skills', 'Symmetrical'],
  },
];

// ── Preview Modal ─────────────────────────────────────────────────────────────

function PreviewModal({ template, onClose }: { template: Template; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-[#141414] border border-white/[0.07] rounded-2xl w-full max-w-4xl flex flex-col shadow-2xl overflow-hidden"
        style={{ height: 'min(85vh, 700px)' }}
      >
        {/* Modal header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.07] flex-shrink-0">
          <div>
            <h3 className="text-white font-semibold text-sm">{template.name}</h3>
            <p className="text-gray-500 text-xs mt-0.5">{template.description}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/[0.06]"
            aria-label="Close preview"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Iframe */}
        <div className="flex-1 bg-[#0a0a0a] relative">
          <iframe
            src={`/api/resume/template-preview/${template.id}`}
            title={`Preview of ${template.name}`}
            className="w-full h-full border-0"
            sandbox="allow-same-origin allow-scripts"
          />
        </div>
      </div>
    </div>
  );
}

// ── Template Card ─────────────────────────────────────────────────────────────

function TemplateCard({
  template,
  onPreview,
  onUse,
}: {
  template: Template;
  onPreview: (t: Template) => void;
  onUse: (t: Template) => void;
}) {
  return (
    <div className="bg-[#141414] border border-white/[0.07] rounded-2xl p-5 flex flex-col gap-4 hover:border-white/[0.13] transition-all group">
      {/* Preview thumbnail placeholder */}
      <div className="w-full aspect-[3/2] bg-[#0a0a0a] rounded-xl border border-white/[0.05] flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-violet-600/10 to-blue-600/10 opacity-0 group-hover:opacity-100 transition-opacity" />
        <span className="text-gray-700 text-xs font-mono select-none">{template.id}</span>
      </div>

      {/* Name + popular badge */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-white font-semibold text-sm leading-snug">{template.name}</h3>
        {template.popular && (
          <span className="flex-shrink-0 flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 uppercase tracking-wide">
            🔥 Popular
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-gray-500 text-xs leading-relaxed -mt-2">{template.description}</p>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5">
        {template.tags.map(tag => (
          <span
            key={tag}
            className="text-[11px] px-2 py-0.5 rounded-full bg-white/[0.05] text-gray-500 border border-white/[0.06]"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-auto pt-1">
        <button
          onClick={() => onPreview(template)}
          className="flex-1 px-3 py-2 rounded-xl text-sm font-medium border border-white/[0.07] text-gray-400 hover:text-white hover:border-white/[0.15] bg-white/[0.03] hover:bg-white/[0.07] transition-all"
        >
          Preview
        </button>
        <button
          onClick={() => onUse(template)}
          className="flex-1 px-3 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white transition-all shadow-lg shadow-violet-900/20"
        >
          Use this template
        </button>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function TemplatesPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null);

  const handleUse = (template: Template) => {
    router.push(`/app/resume?template=${template.id}`);
    showToast(`Template "${template.name}" selected`, 'success');
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-8">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Resume Templates</h1>
        <p className="text-gray-500 text-sm mt-1">Choose a design that stands out</p>
      </div>

      {/* Popular callout */}
      <div className="mb-6 bg-amber-500/10 border border-amber-500/20 rounded-2xl px-5 py-3.5 flex items-center gap-3">
        <span className="text-lg">🔥</span>
        <p className="text-amber-300 text-sm">
          <span className="font-semibold">Popular templates</span>
          {' '}are marked with a flame badge — they have the highest recruiter acceptance rates.
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
        {TEMPLATES.map(template => (
          <TemplateCard
            key={template.id}
            template={template}
            onPreview={setPreviewTemplate}
            onUse={handleUse}
          />
        ))}
      </div>

      {/* Preview modal */}
      {previewTemplate && (
        <PreviewModal
          template={previewTemplate}
          onClose={() => setPreviewTemplate(null)}
        />
      )}
    </div>
  );
}
