import { useState, useEffect } from 'react'
import { profileApi } from '../api/client'

const EMPTY_EXP = { company: '', position: '', start_date: '', end_date: '', description: '', skills: [], is_current: false }
const EMPTY_EDU = { institution: '', degree: '', field: '', graduation_date: '', gpa: '', honors: '' }
const EMPTY_LOC = { city: '', state: '', country: '', remote: false }

export default function ProfilePage() {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    summary: '',
    location: { city: '', state: '', country: '', remote: false },
    skills: [],
    work_experience: [],
    education: [],
    certifications: [],
    preferred_job_levels: [],
    preferred_locations: [],
    preferred_salary_min: '',
    preferred_salary_max: '',
    remote_preference: 'flexible',
    willing_to_relocate: false,
  })

  const [newSkill, setNewSkill] = useState('')
  const [newCert, setNewCert] = useState('')
  const [newExpSkill, setNewExpSkill] = useState({})

  const populateForm = (data) => ({
    full_name: data.full_name || '',
    email: data.email || '',
    phone: data.phone || '',
    summary: data.summary || '',
    location: data.location || { city: '', state: '', country: '', remote: false },
    skills: data.skills || [],
    work_experience: (data.work_experience || []).map((w) => ({
      ...w,
      start_date: w.start_date?.slice(0, 10) || '',
      end_date: w.end_date?.slice(0, 10) || '',
    })),
    education: (data.education || []).map((e) => ({
      ...e,
      graduation_date: e.graduation_date?.slice(0, 10) || '',
      gpa: e.gpa || '',
    })),
    certifications: data.certifications || [],
    preferred_job_levels: data.preferred_job_levels || [],
    preferred_locations: data.preferred_locations || [],
    preferred_salary_min: data.preferred_salary_min || '',
    preferred_salary_max: data.preferred_salary_max || '',
    remote_preference: data.remote_preference || 'flexible',
    willing_to_relocate: data.willing_to_relocate || false,
  })

  useEffect(() => {
    profileApi.getCurrent()
      .then((res) => {
        setProfile(res.data)
        setForm(populateForm(res.data))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const payload = {
        ...form,
        preferred_salary_min: form.preferred_salary_min ? Number(form.preferred_salary_min) : null,
        preferred_salary_max: form.preferred_salary_max ? Number(form.preferred_salary_max) : null,
        work_experience: form.work_experience.map((w) => ({
          ...w,
          start_date: w.start_date ? new Date(w.start_date).toISOString() : null,
          end_date: w.end_date ? new Date(w.end_date).toISOString() : null,
        })),
        education: form.education.map((e) => ({
          ...e,
          graduation_date: e.graduation_date ? new Date(e.graduation_date).toISOString() : null,
          gpa: e.gpa ? Number(e.gpa) : null,
        })),
      }
      if (profile?.user_id) {
        const res = await profileApi.update(profile.user_id, payload)
        setProfile(res.data)
      } else {
        const res = await profileApi.create(payload)
        setProfile(res.data)
      }
      setMessage({ type: 'success', text: 'Profile saved successfully!' })
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save profile' })
    }
    setSaving(false)
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setSaving(true)
    setMessage(null)
    try {
      const res = await profileApi.upload(file)
      setProfile(res.data)
      setForm(populateForm(res.data))
      setMessage({ type: 'success', text: 'Resume uploaded and parsed!' })
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Upload failed' })
    }
    setSaving(false)
  }

  // --- Tag helpers ---
  const addTag = (field, value, setter) => {
    if (value.trim() && !form[field].includes(value.trim())) {
      setForm({ ...form, [field]: [...form[field], value.trim()] })
      setter('')
    }
  }
  const removeTag = (field, value) => {
    setForm({ ...form, [field]: form[field].filter((s) => s !== value) })
  }

  // --- Field helpers ---
  const updateField = (field, value) => setForm({ ...form, [field]: value })
  const updateLocation = (field, value) => setForm({ ...form, location: { ...form.location, [field]: value } })

  // --- Work Experience helpers ---
  const addExperience = () => setForm({ ...form, work_experience: [...form.work_experience, { ...EMPTY_EXP }] })
  const removeExperience = (i) => setForm({ ...form, work_experience: form.work_experience.filter((_, idx) => idx !== i) })
  const updateExperience = (i, field, value) => {
    const updated = [...form.work_experience]
    updated[i] = { ...updated[i], [field]: value }
    if (field === 'is_current' && value) updated[i].end_date = ''
    setForm({ ...form, work_experience: updated })
  }
  const addExpSkill = (i) => {
    const skill = (newExpSkill[i] || '').trim()
    if (skill && !form.work_experience[i].skills.includes(skill)) {
      const updated = [...form.work_experience]
      updated[i] = { ...updated[i], skills: [...updated[i].skills, skill] }
      setForm({ ...form, work_experience: updated })
      setNewExpSkill({ ...newExpSkill, [i]: '' })
    }
  }
  const removeExpSkill = (i, skill) => {
    const updated = [...form.work_experience]
    updated[i] = { ...updated[i], skills: updated[i].skills.filter((s) => s !== skill) }
    setForm({ ...form, work_experience: updated })
  }

  // --- Education helpers ---
  const addEducation = () => setForm({ ...form, education: [...form.education, { ...EMPTY_EDU }] })
  const removeEducation = (i) => setForm({ ...form, education: form.education.filter((_, idx) => idx !== i) })
  const updateEducation = (i, field, value) => {
    const updated = [...form.education]
    updated[i] = { ...updated[i], [field]: value }
    setForm({ ...form, education: updated })
  }

  // --- Preferred Locations helpers ---
  const addPrefLocation = () => setForm({ ...form, preferred_locations: [...form.preferred_locations, { ...EMPTY_LOC }] })
  const removePrefLocation = (i) => setForm({ ...form, preferred_locations: form.preferred_locations.filter((_, idx) => idx !== i) })
  const updatePrefLocation = (i, field, value) => {
    const updated = [...form.preferred_locations]
    updated[i] = { ...updated[i], [field]: value }
    setForm({ ...form, preferred_locations: updated })
  }

  const inputClass = "w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"

  if (loading) return <div className="text-gray-500">Loading profile...</div>

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Profile</h2>
        <div className="flex gap-3">
          <label className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 cursor-pointer transition-colors">
            Upload Resume
            <input type="file" accept=".pdf,.json,.txt" onChange={handleUpload} className="hidden" />
          </label>
          <button onClick={handleSave} disabled={saving}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-400 transition-colors">
            {saving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`mb-4 p-3 rounded-lg text-sm ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message.text}
        </div>
      )}

      <div className="space-y-6">

        {/* ===== Basic Info ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Basic Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input value={form.full_name} onChange={(e) => updateField('full_name', e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" value={form.email} onChange={(e) => updateField('email', e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input value={form.phone} onChange={(e) => updateField('phone', e.target.value)} className={inputClass} />
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Summary</label>
            <textarea value={form.summary} onChange={(e) => updateField('summary', e.target.value)} rows={3} className={inputClass} />
          </div>
        </div>

        {/* ===== Location ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Location</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
              <input value={form.location?.city || ''} onChange={(e) => updateLocation('city', e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
              <input value={form.location?.state || ''} onChange={(e) => updateLocation('state', e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
              <input value={form.location?.country || ''} onChange={(e) => updateLocation('country', e.target.value)} className={inputClass} />
            </div>
          </div>
        </div>

        {/* ===== Skills ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Skills</h3>
          <div className="flex gap-2 mb-3">
            <input value={newSkill} onChange={(e) => setNewSkill(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('skills', newSkill, setNewSkill))}
              placeholder="Add a skill..." className={`flex-1 ${inputClass}`} />
            <button type="button" onClick={() => addTag('skills', newSkill, setNewSkill)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors">Add</button>
          </div>
          <div className="flex flex-wrap gap-2">
            {form.skills.map((skill) => (
              <span key={skill} className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm flex items-center gap-1">
                {skill}
                <button onClick={() => removeTag('skills', skill)} className="text-blue-400 hover:text-blue-700 ml-1">x</button>
              </span>
            ))}
          </div>
        </div>

        {/* ===== Certifications ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Certifications</h3>
          <div className="flex gap-2 mb-3">
            <input value={newCert} onChange={(e) => setNewCert(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('certifications', newCert, setNewCert))}
              placeholder="Add a certification..." className={`flex-1 ${inputClass}`} />
            <button type="button" onClick={() => addTag('certifications', newCert, setNewCert)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors">Add</button>
          </div>
          <div className="flex flex-wrap gap-2">
            {form.certifications.map((cert) => (
              <span key={cert} className="bg-purple-50 text-purple-700 px-3 py-1 rounded-full text-sm flex items-center gap-1">
                {cert}
                <button onClick={() => removeTag('certifications', cert)} className="text-purple-400 hover:text-purple-700 ml-1">x</button>
              </span>
            ))}
          </div>
        </div>

        {/* ===== Work Experience ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-800">Work Experience</h3>
            <button onClick={addExperience}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors">
              + Add Experience
            </button>
          </div>
          {form.work_experience.length === 0 && (
            <p className="text-sm text-gray-400">No work experience added. Click "Add Experience" or upload a resume.</p>
          )}
          <div className="space-y-6">
            {form.work_experience.map((exp, i) => (
              <div key={i} className="border border-gray-200 rounded-lg p-4 relative">
                <button onClick={() => removeExperience(i)}
                  className="absolute top-3 right-3 text-red-400 hover:text-red-600 text-sm">Remove</button>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Position</label>
                    <input value={exp.position} onChange={(e) => updateExperience(i, 'position', e.target.value)} className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                    <input value={exp.company} onChange={(e) => updateExperience(i, 'company', e.target.value)} className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                    <input type="date" value={exp.start_date} onChange={(e) => updateExperience(i, 'start_date', e.target.value)} className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                    <input type="date" value={exp.end_date} onChange={(e) => updateExperience(i, 'end_date', e.target.value)}
                      disabled={exp.is_current} className={`${inputClass} ${exp.is_current ? 'bg-gray-100' : ''}`} />
                    <label className="flex items-center gap-2 mt-1 cursor-pointer">
                      <input type="checkbox" checked={exp.is_current} onChange={(e) => updateExperience(i, 'is_current', e.target.checked)}
                        className="rounded border-gray-300 text-blue-600" />
                      <span className="text-xs text-gray-500">Currently working here</span>
                    </label>
                  </div>
                </div>
                <div className="mt-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea value={exp.description} onChange={(e) => updateExperience(i, 'description', e.target.value)} rows={2} className={inputClass} />
                </div>
                <div className="mt-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Skills</label>
                  <div className="flex gap-2 mb-2">
                    <input value={newExpSkill[i] || ''} onChange={(e) => setNewExpSkill({ ...newExpSkill, [i]: e.target.value })}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addExpSkill(i))}
                      placeholder="Add skill..." className={`flex-1 ${inputClass}`} />
                    <button type="button" onClick={() => addExpSkill(i)}
                      className="bg-gray-200 text-gray-700 px-3 py-2 rounded-lg text-sm hover:bg-gray-300 transition-colors">Add</button>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {exp.skills.map((s) => (
                      <span key={s} className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs flex items-center gap-1">
                        {s}
                        <button onClick={() => removeExpSkill(i, s)} className="text-gray-400 hover:text-gray-700">x</button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ===== Education ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-800">Education</h3>
            <button onClick={addEducation}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors">
              + Add Education
            </button>
          </div>
          {form.education.length === 0 && (
            <p className="text-sm text-gray-400">No education added. Click "Add Education" or upload a resume.</p>
          )}
          <div className="space-y-6">
            {form.education.map((edu, i) => (
              <div key={i} className="border border-gray-200 rounded-lg p-4 relative">
                <button onClick={() => removeEducation(i)}
                  className="absolute top-3 right-3 text-red-400 hover:text-red-600 text-sm">Remove</button>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Institution</label>
                    <input value={edu.institution} onChange={(e) => updateEducation(i, 'institution', e.target.value)} className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Degree</label>
                    <input value={edu.degree} onChange={(e) => updateEducation(i, 'degree', e.target.value)} placeholder="e.g. B.Tech, M.S." className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Field of Study</label>
                    <input value={edu.field} onChange={(e) => updateEducation(i, 'field', e.target.value)} placeholder="e.g. Computer Science" className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Graduation Date</label>
                    <input type="date" value={edu.graduation_date} onChange={(e) => updateEducation(i, 'graduation_date', e.target.value)} className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">GPA</label>
                    <input type="number" step="0.01" value={edu.gpa} onChange={(e) => updateEducation(i, 'gpa', e.target.value)} placeholder="e.g. 3.8" className={inputClass} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Honors</label>
                    <input value={edu.honors} onChange={(e) => updateEducation(i, 'honors', e.target.value)} placeholder="e.g. Magna Cum Laude" className={inputClass} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ===== Preferences ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Preferences</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Remote Preference</label>
              <select value={form.remote_preference} onChange={(e) => updateField('remote_preference', e.target.value)} className={inputClass}>
                <option value="required">Remote Required</option>
                <option value="preferred">Remote Preferred</option>
                <option value="flexible">Flexible</option>
                <option value="not_interested">Not Interested in Remote</option>
              </select>
            </div>
            <div className="flex items-center gap-3 pt-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.willing_to_relocate}
                  onChange={(e) => updateField('willing_to_relocate', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 w-5 h-5" />
                <span className="text-sm font-medium text-gray-700">Willing to Relocate</span>
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Job Levels</label>
              <div className="flex flex-wrap gap-3">
                {['entry', 'junior', 'mid', 'senior', 'lead', 'executive'].map((level) => (
                  <label key={level} className="flex items-center gap-1 cursor-pointer">
                    <input type="checkbox" checked={form.preferred_job_levels.includes(level)}
                      onChange={(e) => {
                        if (e.target.checked) updateField('preferred_job_levels', [...form.preferred_job_levels, level])
                        else updateField('preferred_job_levels', form.preferred_job_levels.filter((l) => l !== level))
                      }}
                      className="rounded border-gray-300 text-blue-600" />
                    <span className="text-sm capitalize text-gray-700">{level}</span>
                  </label>
                ))}
              </div>
            </div>
            <div></div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Salary ($)</label>
              <input type="number" value={form.preferred_salary_min} onChange={(e) => updateField('preferred_salary_min', e.target.value)}
                placeholder="e.g. 80000" className={inputClass} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max Salary ($)</label>
              <input type="number" value={form.preferred_salary_max} onChange={(e) => updateField('preferred_salary_max', e.target.value)}
                placeholder="e.g. 150000" className={inputClass} />
            </div>
          </div>
        </div>

        {/* ===== Preferred Locations ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-800">Preferred Locations</h3>
            <button onClick={addPrefLocation}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors">
              + Add Location
            </button>
          </div>
          {form.preferred_locations.length === 0 && (
            <p className="text-sm text-gray-400">No preferred locations added. Jobs from all locations will be shown.</p>
          )}
          <div className="space-y-3">
            {form.preferred_locations.map((loc, i) => (
              <div key={i} className="flex items-center gap-3">
                <input value={loc.city} onChange={(e) => updatePrefLocation(i, 'city', e.target.value)}
                  placeholder="City" className={`flex-1 ${inputClass}`} />
                <input value={loc.state} onChange={(e) => updatePrefLocation(i, 'state', e.target.value)}
                  placeholder="State" className={`flex-1 ${inputClass}`} />
                <input value={loc.country} onChange={(e) => updatePrefLocation(i, 'country', e.target.value)}
                  placeholder="Country" className={`flex-1 ${inputClass}`} />
                <label className="flex items-center gap-1 cursor-pointer whitespace-nowrap">
                  <input type="checkbox" checked={loc.remote} onChange={(e) => updatePrefLocation(i, 'remote', e.target.checked)}
                    className="rounded border-gray-300 text-blue-600" />
                  <span className="text-xs text-gray-500">Remote</span>
                </label>
                <button onClick={() => removePrefLocation(i)} className="text-red-400 hover:text-red-600 text-sm">Remove</button>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
