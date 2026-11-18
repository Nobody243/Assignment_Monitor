/** The CMS writes exam dates as dd/mm/yyyy. */
export const parseExamDate = (s: string): Date | null => {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec((s ?? '').trim())
  return m ? new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1])) : null
}
