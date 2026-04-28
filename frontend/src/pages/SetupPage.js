import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect } from 'react';
import RegionSelector from '../components/RegionSelector';
import { useRegionState } from '../lib/regionState';
import { useRegions } from '../lib/queries';
import { useNavigate } from 'react-router-dom';
export default function SetupPage() {
    const { region, setRegion, goWithRegion } = useRegionState();
    const navigate = useNavigate();
    const regions = useRegions();
    // 이미 region 이 query 에 있으면 personas 로 자동 진입.
    useEffect(() => {
        if (region) {
            goWithRegion('/personas');
        }
    }, [region, goWithRegion]);
    return (_jsxs("section", { children: [_jsx("h2", { children: "Setup" }), _jsx("p", { className: "muted", children: "\uC2DC\uCCAD\uD560 \uC9C0\uC5ED\uC744 \uC120\uD0DD\uD558\uC138\uC694. URL query param \uC73C\uB85C \uC0C1\uD0DC\uAC00 \uBCF4\uC874\uB418\uBA70, \uC9C1\uC811 \uB9C1\uD06C \uC9C4\uC785 \uC2DC setup \uB2E8\uACC4\uB294 \uAC74\uB108\uB701\uB2C8\uB2E4." }), regions.isLoading ? _jsx("p", { children: "Loading regions\u2026" }) : null, regions.isError ? (_jsxs("p", { style: { color: 'var(--color-fail)' }, children: ["Region \uB85C\uB4DC \uC2E4\uD328: ", regions.error.message] })) : null, regions.isSuccess ? (_jsx(RegionSelector, { regions: regions.data, value: region, onChange: (regionId, contestId) => {
                    setRegion(regionId, contestId);
                    navigate({
                        pathname: '/personas',
                        search: `?region=${regionId}${contestId ? `&contest=${contestId}` : ''}`,
                    });
                } })) : null] }));
}
