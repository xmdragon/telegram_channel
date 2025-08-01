import { useState, useEffect } from 'react'
import axios from 'axios'
import jwt_decode from 'jwt-decode'
import { DataGrid } from '@mui/x-data-grid'
import { Button, TextField, Container, Typography, Dialog, DialogActions, DialogContent, DialogTitle } from '@mui/material'

function App() {
  const [rows, setRows] = useState([])
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [selectedRow, setSelectedRow] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (token) fetchMessages()
  }, [token])

  const fetchMessages = async () => {
    const res = await axios.get('http://gxfc.life:5100/api/messages', {
      headers: { Authorization: `Bearer ${token}` }
    })
    setRows(res.data)
  }

  const handleEdit = async () => {
    await axios.put(`http://gxfc.life:5100/api/message/${selectedRow.id}`,
      { text: selectedRow.text },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    fetchMessages()
    setSelectedRow(null)
  }

  const handleDelete = async (id) => {
    await axios.delete(`http://gxfc.life:5100/api/message/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchMessages()
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    const res = await axios.post('http://gxfc.life:5100/api/login', {
      username: e.target.username.value,
      password: e.target.password.value
    })
    localStorage.setItem('token', res.data.access_token)
    setToken(res.data.access_token)
  }

  const filteredRows = rows.filter(row => row.text.toLowerCase().includes(search.toLowerCase()))

  if (!token) {
    return (
      <Container>
        <form onSubmit={handleLogin}>
          <Typography variant="h5">Login</Typography>
          <TextField name="username" label="Username" fullWidth required />
          <TextField name="password" label="Password" type="password" fullWidth required />
          <Button type="submit" variant="contained" sx={{ mt: 2 }}>Login</Button>
        </form>
      </Container>
    )
  }

  return (
    <Container>
      <Typography variant="h4" gutterBottom>Telegram Manager</Typography>
      <TextField
        label="Search"
        value={search}
        onChange={e => setSearch(e.target.value)}
        fullWidth
        sx={{ mb: 2 }}
      />
      <div style={{ height: 600 }}>
        <DataGrid
          rows={filteredRows}
          columns={[
            { field: 'id', width: 90 },
            { field: 'text', width: 500 },
            { field: 'date', width: 200 },
            {
              field: 'actions',
              headerName: 'Actions',
              width: 180,
              renderCell: (params) => (
                <>
                  <Button onClick={() => setSelectedRow(params.row)} variant="contained" size="small">Edit</Button>
                  <Button onClick={() => handleDelete(params.row.id)} variant="outlined" color="error" size="small" sx={{ ml: 1 }}>Delete</Button>
                </>
              )
            }
          ]}
          pageSize={10}
          rowsPerPageOptions={[10]}
        />
      </div>
      <Dialog open={!!selectedRow} onClose={() => setSelectedRow(null)}>
        <DialogTitle>Edit Message</DialogTitle>
        <DialogContent>
          <TextField
            multiline fullWidth
            value={selectedRow?.text || ''}
            onChange={(e) => setSelectedRow({...selectedRow, text: e.target.value})}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedRow(null)}>Cancel</Button>
          <Button onClick={handleEdit}>Save</Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default App
