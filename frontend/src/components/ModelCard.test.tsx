import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import ModelCard from './ModelCard';

describe('ModelCard Component', () => {
  it('renders model card name and task badge', () => {
    const model = {
      id: 'm-1',
      name: 'ResNet50-Classifier',
      description: 'Image classifier trained on CIFAR-10',
      task: 'vision',
      architecture: 'cnn',
      versions: [
        {
          version: 1,
          run_id: 'r-1',
          registered_at: 1700000000,
          tags: ['production'],
          metrics: { accuracy: 0.942, loss: 0.12 },
          parent_version: null,
        },
      ],
      created_at: 1700000000,
    };

    render(<ModelCard model={model} selected={false} onClick={vi.fn()} />);
    expect(screen.getByText('ResNet50-Classifier')).toBeDefined();
    expect(screen.getByText('vision')).toBeDefined();
    expect(screen.getByText(/Architecture:\s*cnn/)).toBeDefined();
  });

  it('renders best metric and tag badges', () => {
    const model = {
      id: 'm-2',
      name: 'BERT-Sentiment',
      description: 'Transformer NLP classifier',
      task: 'nlp',
      architecture: 'transformer',
      versions: [
        {
          version: 2,
          run_id: 'r-2',
          registered_at: 1700000000,
          tags: ['staging'],
          metrics: { f1_score: 0.91 },
          parent_version: 1,
        },
      ],
      created_at: 1700000000,
    };

    render(<ModelCard model={model} selected={true} onClick={vi.fn()} />);
    expect(screen.getByText('0.9100')).toBeDefined();
    expect(screen.getByText('staging')).toBeDefined();
    expect(screen.getByText('Best metric')).toBeDefined();
  });

  it('renders version count for model without versions', () => {
    const model = {
      id: 'm-3',
      name: 'Tiny-MLP',
      description: 'Tabular MLP',
      task: 'tabular',
      architecture: 'mlp',
      versions: [],
      created_at: 1700000000,
    };

    render(<ModelCard model={model} selected={false} onClick={vi.fn()} />);
    expect(screen.getByText('Tiny-MLP')).toBeDefined();
    expect(screen.getByText('0 versions')).toBeDefined();
  });
});
