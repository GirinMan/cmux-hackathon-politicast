import { jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
import { Navigate } from 'react-router-dom';
import { useRegionState } from '../lib/regionState';
/** Public 페이지가 region query param 을 강제하도록 wrap. */
export default function RequireRegion({ children }) {
    const { region } = useRegionState();
    if (!region)
        return _jsx(Navigate, { to: "/", replace: true });
    return _jsx(_Fragment, { children: children(region) });
}
