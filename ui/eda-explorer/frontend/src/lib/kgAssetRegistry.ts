import choWonJin from '../assets/kg/people/cho_won_jin.png'
import chooKyungHo from '../assets/kg/people/choo_kyung_ho.jpg'
import anTaeWook from '../assets/kg/people/an_tae_wook.jpeg'
import haJungWoo from '../assets/kg/people/ha_jung_woo.png'
import hanDongHoon from '../assets/kg/people/han_dong_hoon.png'
import hanMinSu from '../assets/kg/people/han_min_su.png'
import hongSeongJu from '../assets/kg/people/hong_seong_ju.jpg'
import jeonJaeSoo from '../assets/kg/people/jeon_jae_soo.jpg'
import jungChungRae from '../assets/kg/people/jung_chung_rae.jpg'
import jungWonOh from '../assets/kg/people/jung_won_oh.jpg'
import kangGiJung from '../assets/kg/people/kang_gi_jung.jpg'
import kimMinSu from '../assets/kg/people/kim_min_su.png'
import kimBooKyum from '../assets/kg/people/kim_boo_kyum.jpg'
import leeJinSook from '../assets/kg/people/lee_jin_sook.jpg'
import minHyeongBae from '../assets/kg/people/min_hyeong_bae.jpg'
import ohSeHoon from '../assets/kg/people/oh_se_hoon.jpg'
import parkHeongJoon from '../assets/kg/people/park_heong_joon.jpg'
import parkMinSik from '../assets/kg/people/park_min_sik.jpg'
import seoJaeHun from '../assets/kg/people/seo_jae_hun.jpg'
import seoWangJin from '../assets/kg/people/seo_wang_jin.jpg'
import yooYoungHa from '../assets/kg/people/yoo_young_ha.jpg'
import democraticParty from '../assets/kg/parties/democratic_party.png'
import ourRepublicanParty from '../assets/kg/parties/our_republican_party.svg'
import peoplePowerParty from '../assets/kg/parties/people_power_party.svg'
import rebuildingKoreaParty from '../assets/kg/parties/rebuilding_korea_party.svg'

type Attrs = Record<string, unknown> | null | undefined

const PEOPLE_ASSETS: Record<string, string> = {
  'Candidate:c_daegu_dpk': kimBooKyum,
  c_daegu_dpk: kimBooKyum,
  김부겸: kimBooKyum,
  'Candidate:c_daegu_ppp_choo': chooKyungHo,
  'Person:person_choo_kyungho': chooKyungHo,
  c_daegu_ppp_choo: chooKyungHo,
  추경호: chooKyungHo,
  'Candidate:c_seoul_ppp': ohSeHoon,
  c_seoul_ppp: ohSeHoon,
  오세훈: ohSeHoon,
  'Candidate:c_seoul_dpk': jungWonOh,
  c_seoul_dpk: jungWonOh,
  정원오: jungWonOh,
  'Candidate:c_busan_indep_han': hanDongHoon,
  c_busan_indep_han: hanDongHoon,
  한동훈: hanDongHoon,
  'Candidate:c_busan_dpk': haJungWoo,
  c_busan_dpk: haJungWoo,
  하정우: haJungWoo,
  'Candidate:c_busan_ppp': parkMinSik,
  c_busan_ppp: parkMinSik,
  박민식: parkMinSik,
  'Candidate:c_daegu_ourrep': choWonJin,
  c_daegu_ourrep: choWonJin,
  조원진: choWonJin,
  'Candidate:c_daegu_ppp_yoo': yooYoungHa,
  c_daegu_ppp_yoo: yooYoungHa,
  유영하: yooYoungHa,
  'Candidate:c_gwangju_dpk_alt': minHyeongBae,
  c_gwangju_dpk_alt: minHyeongBae,
  민형배: minHyeongBae,
  'Candidate:c_gwangju_ppp': anTaeWook,
  c_gwangju_ppp: anTaeWook,
  안태욱: anTaeWook,
  'Candidate:c_gwangju_rebuild': seoWangJin,
  c_gwangju_rebuild: seoWangJin,
  서왕진: seoWangJin,
  'Candidate:c_dalseo_dpk': seoJaeHun,
  c_dalseo_dpk: seoJaeHun,
  서재헌: seoJaeHun,
  'Candidate:c_dalseo_ppp_kim': kimMinSu,
  c_dalseo_ppp_kim: kimMinSu,
  김민수: kimMinSu,
  'Candidate:c_dalseo_ppp_hong': hongSeongJu,
  c_dalseo_ppp_hong: hongSeongJu,
  홍성주: hongSeongJu,
  'Candidate:c_seoul_rebuild': hanMinSu,
  c_seoul_rebuild: hanMinSu,
  한민수: hanMinSu,
  'Person:p_lee_js': leeJinSook,
  'Person:person_lee_jinsook': leeJinSook,
  p_lee_js: leeJinSook,
  이진숙: leeJinSook,
  'Person:p_park_hj': parkHeongJoon,
  p_park_hj: parkHeongJoon,
  박형준: parkHeongJoon,
  'Person:p_jeon_js': jeonJaeSoo,
  p_jeon_js: jeonJaeSoo,
  전재수: jeonJaeSoo,
  'Person:p_jcr': jungChungRae,
  p_jcr: jungChungRae,
  정청래: jungChungRae,
  'Candidate:c_gwangju_dpk': kangGiJung,
  c_gwangju_dpk: kangGiJung,
  강기정: kangGiJung,
}

const PARTY_ASSETS: Record<string, string> = {
  'Party:p_dem': democraticParty,
  p_dem: democraticParty,
  더불어민주당: democraticParty,
  민주당: democraticParty,
  DPK: democraticParty,
  'Party:p_ppp': peoplePowerParty,
  p_ppp: peoplePowerParty,
  국민의힘: peoplePowerParty,
  PPP: peoplePowerParty,
  'Party:p_rebuild': rebuildingKoreaParty,
  p_rebuild: rebuildingKoreaParty,
  조국혁신당: rebuildingKoreaParty,
  'Party:p_ourrep': ourRepublicanParty,
  p_ourrep: ourRepublicanParty,
  우리공화당: ourRepublicanParty,
}

export function kgPersonAsset(input: {
  id?: string | null
  label?: string | null
  attrs?: Attrs
}) {
  return lookupAsset(PEOPLE_ASSETS, [
    input.id,
    input.label,
    readAttr(input.attrs, 'candidate_id'),
    readAttr(input.attrs, 'person_id'),
    readAttr(input.attrs, 'name'),
    readAttr(input.attrs, 'speaker'),
  ])
}

export function kgPartyAsset(input: {
  id?: string | null
  label?: string | null
  attrs?: Attrs
}) {
  return lookupAsset(PARTY_ASSETS, [
    input.id,
    input.label,
    readAttr(input.attrs, 'party_id'),
    readAttr(input.attrs, 'party'),
    readAttr(input.attrs, 'party_name'),
    readAttr(input.attrs, 'affiliation'),
  ])
}

export function kgNodeAsset(input: {
  id?: string | null
  label?: string | null
  kind?: string | null
  attrs?: Attrs
}) {
  if (input.kind === 'Party') return kgPartyAsset(input)
  if (input.kind === 'Candidate' || input.kind === 'Person') {
    return kgPersonAsset(input) ?? kgPartyAsset(input)
  }
  return kgPartyAsset(input) ?? kgPersonAsset(input)
}

function lookupAsset(registry: Record<string, string>, keys: Array<unknown>) {
  for (const key of keys) {
    const value = normalizeKey(key)
    if (value && registry[value]) return registry[value]
  }
  return null
}

function readAttr(attrs: Attrs, key: string) {
  if (!attrs) return ''
  return attrs[key]
}

function normalizeKey(value: unknown) {
  if (typeof value !== 'string') return ''
  return value.trim()
}
