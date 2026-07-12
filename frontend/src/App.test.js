import { render, screen } from '@testing-library/react';
import App from './App';

test('renders sign in screen', () => {
  render(<App />);
  const heading = screen.getByText(/RAG Assistant/i);
  expect(heading).toBeInTheDocument();
});
