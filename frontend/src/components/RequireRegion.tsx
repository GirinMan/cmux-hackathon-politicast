import { Navigate } from 'react-router-dom';

import { useRegionState } from '../lib/regionState';

interface Props {
  children: (region: string) => React.ReactNode;
}

/** Public 페이지가 region query param 을 강제하도록 wrap. */
export default function RequireRegion({ children }: Props) {
  const { region } = useRegionState();
  if (!region) return <Navigate to="/" replace />;
  return <>{children(region)}</>;
}
