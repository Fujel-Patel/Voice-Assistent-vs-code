import React from 'react';
import './setup';
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Canvas } from '@react-three/fiber';
import GeminiBlob from '../components/GeminiBlob';

describe('GeminiBlob Component', () => {
  it('renders without crashing even outside a real webgl context', () => {
    // react-three-fiber handles the fallback elegantly in most test setups
    const { container } = render(
      <Canvas>
        <GeminiBlob state="LISTENING" audioLevel={0.5} />
      </Canvas>
    );
    expect(container).toBeDefined();
  });
});
