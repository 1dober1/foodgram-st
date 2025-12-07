import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

test('renders app without crashing', () => {
  // The main issue was that App uses Router components but wasn't wrapped in a Router
  // By wrapping it with MemoryRouter, the Router context is provided
  const { container } = render(
    <MemoryRouter>
      <App />
    </MemoryRouter>
  );
  // If we get here without errors, the Router issue is fixed
  expect(container).toBeTruthy();
});
