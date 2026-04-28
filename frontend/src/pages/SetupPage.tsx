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

  return (
    <section>
      <h2>Setup</h2>
      <p className="muted">
        시청할 지역을 선택하세요. URL query param 으로 상태가 보존되며, 직접 링크 진입 시 setup 단계는 건너뜁니다.
      </p>

      {regions.isLoading ? <p>Loading regions…</p> : null}
      {regions.isError ? (
        <p style={{ color: 'var(--color-fail)' }}>
          Region 로드 실패: {(regions.error as Error).message}
        </p>
      ) : null}

      {regions.isSuccess ? (
        <RegionSelector
          regions={regions.data}
          value={region}
          onChange={(regionId, contestId) => {
            setRegion(regionId, contestId);
            navigate({
              pathname: '/personas',
              search: `?region=${regionId}${contestId ? `&contest=${contestId}` : ''}`,
            });
          }}
        />
      ) : null}
    </section>
  );
}
