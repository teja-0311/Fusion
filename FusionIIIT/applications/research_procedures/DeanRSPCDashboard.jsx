/**
 * Dean RSPC Dashboard Component
 * Displays role-specific dashboard data for Dean RSPC role
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
  AlertCircle, Information, DollarSign, FileText
} from 'react-feather';
import axios from 'axios';

const DeanRSPCDashboard = () => {
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
        Dean RSPC Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Role Overview Card */}
        <Grid item xs={12}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
            <CardContent>
              <Typography variant="h5" sx={{ mb: 2 }}>
                Your Role &amp; Responsibilities
              </Typography>
              <List sx={{ color: 'white' }}>
                <ListItem>
                  <ListItemText
                    primary="• You approve large expenditures &gt; ₹200,000"
                    primaryTypographyProps={{ sx: { color: 'white' } }}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="• You oversee all HOD approvals"
                    primaryTypographyProps={{ sx: { color: 'white' } }}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="• You set expenditure policies and guidelines"
                    primaryTypographyProps={{ sx: { color: 'white' } }}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="• You review research budget allocations"
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
                        {dashboard.dean_pending_count || 0}
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
                        Total Budget
                      </Typography>
                      <Typography variant="h4">
                        ₹{(dashboard.total_budget || 0).toLocaleString()}
                      </Typography>
                    </Box>
                    <DollarSign size={40} color="#4caf50" />
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
                        Approved Amount
                      </Typography>
                      <Typography variant="h4">
                        ₹{(dashboard.approved_amount || 0).toLocaleString()}
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
                        Pending Amount
                      </Typography>
                      <Typography variant="h4">
                        ₹{(dashboard.pending_amount || 0).toLocaleString()}
                      </Typography>
                    </Box>
                    <Clock size={40} color="#ff5722" />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Pending Approvals Table */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Expenditures Awaiting Your Approval
                  </Typography>
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                          <TableCell>Expenditure ID</TableCell>
                          <TableCell>Project</TableCell>
                          <TableCell>Amount</TableCell>
                          <TableCell>Category</TableCell>
                          <TableCell>HOD</TableCell>
                          <TableCell>Requested Date</TableCell>
                          <TableCell>Action</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {dashboard.pending_approvals && dashboard.pending_approvals.map((expenditure) => (
                          <TableRow key={expenditure.eid}>
                            <TableCell>{expenditure.eid}</TableCell>
                            <TableCell>{expenditure.project_name}</TableCell>
                            <TableCell>₹{expenditure.amount.toLocaleString()}</TableCell>
                            <TableCell>{expenditure.category}</TableCell>
                            <TableCell>{expenditure.hod_name}</TableCell>
                            <TableCell>{new Date(expenditure.request_date).toLocaleDateString()}</TableCell>
                            <TableCell>
                              <a href={`/rspc/expenditures/${expenditure.eid}/`} style={{ color: '#667eea' }}>
                                Review
                              </a>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                  {(!dashboard.pending_approvals || dashboard.pending_approvals.length === 0) && (
                    <Typography sx={{ py: 2, textAlign: 'center', color: '#999' }}>
                      No pending approvals
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

export default DeanRSPCDashboard;
