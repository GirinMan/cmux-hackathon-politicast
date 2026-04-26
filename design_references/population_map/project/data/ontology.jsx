// 온톨로지 9차원 카테고리 데이터
// region · province · district · age_group · sex · education_level · occupation · family_type · housing_type

const ONTOLOGY_CATEGORIES = [
  { id: "region",          label: "Region",          color: "#3aa6c9", shape: "diamond", count: 6  },
  { id: "province",        label: "Province",        color: "#7bd389", shape: "square",  count: 12 },
  { id: "district",        label: "District",        color: "#34a39a", shape: "circle",  count: 12 },
  { id: "age_group",       label: "AgeGroup",        color: "#e8a93a", shape: "circle",  count: 8  },
  { id: "sex",             label: "Sex",             color: "#d97a6c", shape: "triangle",count: 2  },
  { id: "education_level", label: "EducationLevel",  color: "#9b8bd1", shape: "circle",  count: 7  },
  { id: "occupation",      label: "Occupation",      color: "#d96370", shape: "pin",     count: 12 },
  { id: "family_type",     label: "FamilyType",      color: "#c97aa8", shape: "triangle",count: 12 },
  { id: "housing_type",    label: "HousingType",     color: "#8a96a8", shape: "diamond", count: 6  },
];

// 대표 노드 (Top nodes)
const TOP_NODES = [
  { label: "아파트",          category: "housing_type",    pct: 62.1 },
  { label: "여자",            category: "sex",             pct: 50.4 },
  { label: "남자",            category: "sex",             pct: 49.6 },
  { label: "구직",            category: "occupation",      pct: 36.7 },
  { label: "고등학교",        category: "education_level", pct: 33.1 },
  { label: "4년제 대학교",    category: "education_level", pct: 27.1 },
  { label: "배우자·자녀와 거주", category: "family_type",  pct: 27.0 },
  { label: "경기",            category: "region",          pct: 26.2 },
  { label: "배우자와 거주",   category: "family_type",     pct: 20.6 },
  { label: "50–59",           category: "age_group",       pct: 19.9 },
];

// 카테고리별 멤버 (각 차원의 실제 값들)
const CATEGORY_MEMBERS = {
  age_group: ["10대","19–29","30–39","40–49","50–59","60–69","70+","무응답"],
  sex: ["남자","여자"],
  education_level: ["초등학교","중학교","고등학교","2~3년제 전문대","4년제 대학교","대학원","무응답"],
  occupation: ["구직","사무직","서비스","판매","기능원","장치·기계","전문가","관리자","농림어업","단순노무","학생","무직"],
  family_type: ["1인가구","배우자와 거주","배우자·자녀와 거주","자녀와 거주","부모와 거주","조부모·부모와","3세대 동거","친척과","비혈연","독신","사별","기타"],
  housing_type: ["아파트","단독주택","연립·다세대","오피스텔","원룸","주택 이외 거처"],
};

// 지역별 온톨로지 시그니처 (지역 특성에 따른 분포 차이)
// 각 지역마다 "이 지역이 강한 카테고리"가 다르다
const REGION_SIGNATURES = {
  seoul:     { dominant: ["아파트","사무직","4년제 대학교","1인가구","30–39"], skew: "metro-young" },
  busan:     { dominant: ["아파트","서비스","고등학교","배우자·자녀와 거주","50–59"], skew: "metro-mid" },
  daegu:     { dominant: ["아파트","서비스","고등학교","배우자·자녀와 거주","40–49"], skew: "metro-mid" },
  incheon:   { dominant: ["아파트","사무직","고등학교","배우자·자녀와 거주","40–49"], skew: "metro-mid" },
  gwangju:   { dominant: ["아파트","서비스","4년제 대학교","배우자·자녀와 거주","30–39"], skew: "metro-young" },
  daejeon:   { dominant: ["아파트","사무직","4년제 대학교","배우자·자녀와 거주","30–39"], skew: "metro-young" },
  ulsan:     { dominant: ["아파트","장치·기계","고등학교","배우자·자녀와 거주","40–49"], skew: "industrial" },
  sejong:    { dominant: ["아파트","사무직","4년제 대학교","배우자·자녀와 거주","30–39"], skew: "admin" },
  gyeonggi:  { dominant: ["아파트","사무직","고등학교","배우자·자녀와 거주","40–49"], skew: "metro-mid" },
  gangwon:   { dominant: ["단독주택","서비스","고등학교","배우자와 거주","60–69"], skew: "rural" },
  chungbuk:  { dominant: ["아파트","기능원","고등학교","배우자·자녀와 거주","50–59"], skew: "rural" },
  chungnam:  { dominant: ["단독주택","농림어업","고등학교","배우자와 거주","60–69"], skew: "rural" },
  jeonbuk:   { dominant: ["단독주택","농림어업","고등학교","배우자와 거주","60–69"], skew: "rural" },
  jeonnam:   { dominant: ["단독주택","농림어업","중학교","배우자와 거주","70+"], skew: "rural-aged" },
  gyeongbuk: { dominant: ["단독주택","농림어업","고등학교","배우자와 거주","60–69"], skew: "rural-aged" },
  gyeongnam: { dominant: ["아파트","기능원","고등학교","배우자·자녀와 거주","50–59"], skew: "industrial" },
  jeju:      { dominant: ["단독주택","농림어업","고등학교","배우자와 거주","50–59"], skew: "island" },
};

window.ONTOLOGY_CATEGORIES = ONTOLOGY_CATEGORIES;
window.TOP_NODES = TOP_NODES;
window.CATEGORY_MEMBERS = CATEGORY_MEMBERS;
window.REGION_SIGNATURES = REGION_SIGNATURES;
