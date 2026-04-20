/**
 * HOD (Head of Department) Dashboard Component
 * Displays role-specific dashboard data for HOD role
 * UC-003: Dashboard Implementation
 */

import React, { useState, useEffect } from 'react';
import {
  Container, Grid, Paper, Card, CardContent, Typography,
  Box, Badge, LinearProgress, List, ListItem, ListItemText,
  Alert, CircularProgress, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow
} from '@mui/material';
import {
  TrendingUp, TrendingDown, Clock, CheckCircle,
  AlertCircle, Information, DollarSign, Users
} from 'react-feather';
import axios from 'axios';

const HODBasedDashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('authToken');
      const response = await axios.get('/rspc/api/dashboard/', {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });
      setDashboard(response.data);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch dashboard');
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h3" sx={{ mb: 4, fontWeight: 'bold' }}>
        HOD (Head of Department) Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Role Overview Card */}
        <Grid item xs={12}>
          <Card sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
            <CardContent>
              <Typography variant="h5" sx={{ mb: 2 }}>
                Your Role &amp; Responsibilities
              </Typography>
              <List sx={{ color: 'white' }}>
                <ListItem>
                  <ListItemText
                    primary="• Expenditures &gt; ₹200,000 go directly to RSPC Admin"
                    primaryTypographyProps={{ sx: { color: 'white' } }}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="• You approve expenditures from ₹50,000 to ₹200,000"
                    primaryTypographyProps={{ sx: { color: 'white' } }}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="• You review faculty research proposals"
                    primaryTypographyProps={{ sx: { color: 'white' } }}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="• You manage departmental budget allocation"
                    primaryTypographyProps={{ sx: { color: 'white' } }}
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Stats Grid */}
        {dashboard && (
          <>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="textSecondary" gutterBottom>
                        Pending Approvals
                      </Typography>
                      <Typography variant="h4">
                        {dashboard.hod_pending_count || 0}
                      </Typography>
                    </Box>
                    <AlertCircle size={40} color="#ff9800" />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="textSecondary" gutterBottom>
                        Pending Amount
                      </Typography>
                      <Typography variant="h4">
                        ₹{(dashboard.hod_pending_amount || 0).toLocaleString()}
                      </Typography>
                    </Box>
                    <DollarSign size={40} color="#ff5722" />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="textSecondary" gutterBottom>
                        Approved This Month
                      </Typography>
                      <Typography variant="h4">
                        {dashboard.hod_approved_count || 0}
                      </Typography>
                    </Box>
                    <CheckCircle size={40} color="#2196f3" />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="textSecondary" gutterBottom>
                        Faculty in Department
                      </Typography>
                      <Typography variant="h4">
                        {dashboard.faculty_count || 0}
                      </Typography>
                    </Box>
                    <Users size={40} color="#9c27b0" />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Pending Approvals Table */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Expenditures Awaiting Your Approval (₹50,000 - ₹200,000)
                  </Typography>
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                          <TableCell>Expenditure ID</TableCell>
                          <TableCell>Faculty</TableCell>
                          <TableCell>Project</TableCell>
                          <TableCell>Amount</TableCell>
                          <TableCell>Category</TableCell>
                          <TableCell>Submitted Date</TableCell>
                          <TableCell>Action</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {dashboard.hod_pending_approvals && dashboard.hod_pending_approvals.map((expenditure) => (
                          <TableRow key={expenditure.eid}>
                            <TableCell>{expenditure.eid}</TableCell>
                            <TableCell>{expenditure.faculty_name}</TableCell>
                            <TableCell>{expenditure.project_name}</TableCell>
                            <TableCell>₹{expenditure.amount.toLocaleString()}</TableCell>
                            <TableCell>{expenditure.category}</TableCell>
                            <TableCell>{new Date(expenditure.request_date).toLocaleDateString()}</TableCell>
                            <TableCell>
                              <a href={`/rspc/expenditures/${expenditure.eid}/`} style={{ color: '#f5576c' }}>
                                Review
                              </a>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                  {(!dashboard.hod_pending_approvals || dashboard.hod_pending_approvals.length === 0) && (
                    <Typography sx={{ py: 2, textAlign: 'center', color: '#999' }}>
                      No pending approvals
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Escalated Approvals */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Large Expenditures Sent to RSPC (&gt; ₹200,000)
                  </Typography>
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                          <TableCell>Expenditure ID</TableCell>
                          <TableCell>Faculty</TableCell>
                          <TableCell>Amount</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Sent Date</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {dashboard.escalated_approvals && dashboard.escalated_approvals.map((expenditure) => (
                          <TableRow key={expenditure.eid}>
                            <TableCell>{expenditure.eid}</TableCell>
                            <TableCell>{expenditure.faculty_name}</TableCell>
                            <TableCell>₹{expenditure.amount.toLocaleString()}</TableCell>
                            <TableCell>
                              <Badge badgeContent={expenditure.status} sx={{ background: '#f5576c' }}>
                                In Review
                              </Badge>
                            </TableCell>
                            <TableCell>{new Date(expenditure.escalation_date).toLocaleDateString()}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                  {(!dashboard.escalated_approvals || dashboard.escalated_approvals.length === 0) && (
                    <Typography sx={{ py: 2, textAlign: 'center', color: '#999' }}>
                      No escalated approvals
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Recent Actions */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Recent Approvals
                  </Typography>
                  <List>
                    {dashboard.recent_approvals && dashboard.recent_approvals.map((approval, index) => (
                      <ListItem key={index} divider>
                        <ListItemText
                          primary={`Approved ₹${approval.amount.toLocaleString()} for ${approval.project_name}`}
                          secondary={new Date(approval.approved_date).toLocaleString()}
                        />
                      </ListItem>
                    ))}
                  </List>
                  {(!dashboard.recent_approvals || dashboard.recent_approvals.length === 0) && (
                    <Typography sx={{ py: 2, textAlign: 'center', color: '#999' }}>
                      No recent approvals
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </>
        )}
      </Grid>
    </Container>
  );
};

export default HODBasedDashboard;
