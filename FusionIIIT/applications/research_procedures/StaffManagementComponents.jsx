/**
 * Staff Management Frontend Components (React + Mantine)
 * Comprehensive UI for UC-007, UC-008, UC-026, UC-027
 */

import React, { useState, useEffect } from 'react';
import {
  Container, Paper, Button, Text, Badge, Group, Stack, Grid,
  TextInput, Select, NumberInput, DatePickerInput, FileInput,
  Textarea, Card, Table, Modal, Loading, Alert, Progress,
  MultiSelect, Tabs, Timeline, ActionIcon, Menu, Popover, Checkbox,
  Dialog, Notification, Title, Divider, Box
} from '@mantine/core';
import { IconAlertCircle, IconCheck, IconX, IconClock, IconUpload } from '@tabler/icons-react';
import axios from 'axios';

const API_URL = '/api/rspc';

// ============================================================================
// 1. STAFF REQUEST FORM (UC-007)
// ============================================================================

export const StaffRequestForm = () => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    project_id: '',
    person: '',
    uname: '',
    biodata_number: '',
    type: '',
    salary: 0,
    no_of_positions: 1,
    qualification: '',
    experience: 0,
    has_funds: false,
    post_on_website: false,
    eligibility: '',
    start_date: null,
    duration: 12,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/staff/`, formData);
      Notification.show({
        title: 'Success',
        message: 'Staff request created successfully',
        color: 'green',
        icon: <IconCheck />,
      });
      // Reset form and redirect
      window.location.href = `/staff/${response.data.sid}`;
    } catch (error) {
      Notification.show({
        title: 'Error',
        message: error.response?.data?.error || 'Failed to create staff request',
        color: 'red',
        icon: <IconX />,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container>
      <Paper p="md" shadow="sm" withBorder>
        <Title order={2} mb="md">Request Staff Appointment (UC-007)</Title>
        
        <form onSubmit={handleSubmit}>
          <Stack spacing="md">
            {/* Project Selection */}
            <Select
              label="Project"
              placeholder="Select project"
              data={[]}  // Load from API
              value={formData.project_id}
              onChange={(value) => setFormData({ ...formData, project_id: value })}
              required
            />

            {/* Personal Information */}
            <TextInput
              label="Full Name"
              placeholder="Enter staff member name"
              value={formData.person}
              onChange={(e) => setFormData({ ...formData, person: e.currentTarget.value })}
              required
            />

            <TextInput
              label="Username"
              placeholder="Username"
              value={formData.uname}
              onChange={(e) => setFormData({ ...formData, uname: e.currentTarget.value })}
              required
            />

            <TextInput
              label="Biodata Number"
              value={formData.biodata_number}
              onChange={(e) => setFormData({ ...formData, biodata_number: e.currentTarget.value })}
            />

            {/* Position Details */}
            <Select
              label="Position Type"
              placeholder="Select position"
              data={[
                { value: 'RA', label: 'Research Associate' },
                { value: 'SRF', label: 'Senior Research Fellow' },
                { value: 'JRF', label: 'Junior Research Fellow' },
                { value: 'PROJECT_ASSISTANT', label: 'Project Assistant' },
                { value: 'PROJECT_SCIENTIST', label: 'Project Scientist' },
              ]}
              value={formData.type}
              onChange={(value) => setFormData({ ...formData, type: value })}
              required
            />

            <NumberInput
              label="Number of Positions"
              placeholder="1"
              min={1}
              value={formData.no_of_positions}
              onChange={(value) => setFormData({ ...formData, no_of_positions: value })}
            />

            <Textarea
              label="Qualification"
              placeholder="Required qualifications (e.g., B.Tech, M.Tech)"
              value={formData.qualification}
              onChange={(e) => setFormData({ ...formData, qualification: e.currentTarget.value })}
            />

            <NumberInput
              label="Experience (Years)"
              min={0}
              value={formData.experience}
              onChange={(value) => setFormData({ ...formData, experience: value })}
            />

            <NumberInput
              label="Monthly Salary"
              min={0}
              value={formData.salary}
              onChange={(value) => setFormData({ ...formData, salary: value })}
            />

            <DatePickerInput
              label="Start Date"
              value={formData.start_date}
              onChange={(date) => setFormData({ ...formData, start_date: date })}
              required
            />

            <NumberInput
              label="Duration (Months)"
              min={1}
              max={60}
              value={formData.duration}
              onChange={(value) => setFormData({ ...formData, duration: value })}
            />

            <Group>
              <Checkbox
                label="Has Funds Available"
                checked={formData.has_funds}
                onChange={(e) => setFormData({ ...formData, has_funds: e.currentTarget.checked })}
              />
              <Checkbox
                label="Post on Website"
                checked={formData.post_on_website}
                onChange={(e) => setFormData({ ...formData, post_on_website: e.currentTarget.checked })}
              />
            </Group>

            <Button type="submit" loading={loading} fullWidth>
              Create Staff Request
            </Button>
          </Stack>
        </form>
      </Paper>
    </Container>
  );
};

// ============================================================================
// 2. COMMITTEE SELECTION FORM (UC-026, BR-RSPC-12)
// ============================================================================

export const CommitteeSelection = ({ staffId }) => {
  const [loading, setLoading] = useState(false);
  const [members, setMembers] = useState([]);
  const [selectedMembers, setSelectedMembers] = useState([]);
  const [deadline, setDeadline] = useState(null);
  const [committeeMembers, setCommitteeMembers] = useState([]);

  useEffect(() => {
    // Load available PI-eligible faculty members
    loadFacultyMembers();
  }, []);

  const loadFacultyMembers = async () => {
    try {
      const response = await axios.get(`${API_URL}/staff/pi-eligible-members/`);
      setMembers(response.data);
    } catch (error) {
      console.error('Failed to load faculty members', error);
    }
  };

  const handleAddMember = (memberId) => {
    const member = members.find(m => m.id === parseInt(memberId));
    if (member && !committeeMembers.find(m => m.id === member.id)) {
      setCommitteeMembers([...committeeMembers, member]);
      setSelectedMembers([...selectedMembers, memberId]);
    }
  };

  const handleRemoveMember = (memberId) => {
    setCommitteeMembers(committeeMembers.filter(m => m.id !== parseInt(memberId)));
    setSelectedMembers(selectedMembers.filter(id => id !== memberId));
  };

  const handleSubmit = async () => {
    if (selectedMembers.length < 3) {
      Notification.show({
        title: 'Error',
        message: 'BR-RSPC-12: Minimum 3 PI-eligible members required',
        color: 'red',
      });
      return;
    }

    if (!deadline) {
      Notification.show({
        title: 'Error',
        message: 'Please set a deadline',
        color: 'red',
      });
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API_URL}/staff/${staffId}/committee/create/`, {
        member_ids: selectedMembers.map(id => parseInt(id)),
        deadline: deadline.toISOString(),
        name: 'Staff Selection Committee',
      });

      Notification.show({
        title: 'Success',
        message: 'Committee created successfully (BR-RSPC-12 validated)',
        color: 'green',
      });
    } catch (error) {
      Notification.show({
        title: 'Error',
        message: error.response?.data?.error || 'Failed to create committee',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container>
      <Paper p="md" shadow="sm" withBorder>
        <Title order={2} mb="md">Create Selection Committee (UC-026)</Title>
        
        <Alert icon={<IconAlertCircle />} color="blue" mb="md">
          BR-RSPC-12: Committee must have minimum 3 PI-eligible members (Professor/Assoc/Asst Prof)
        </Alert>

        <Stack spacing="md">
          <DatePickerInput
            label="Committee Deadline"
            placeholder="Select deadline"
            value={deadline}
            onChange={setDeadline}
            minDate={new Date()}
            required
          />

          <div>
            <Text weight={500} mb="xs">Select Faculty Members</Text>
            <Text size="sm" color="dimmed" mb="md">
              Must select 3 or more PI-eligible members
            </Text>
            
            <Select
              placeholder="Search and add faculty member"
              data={members.map(m => ({
                value: m.id.toString(),
                label: `${m.name} (${m.designation})`,
              }))}
              onChange={handleAddMember}
              searchable
            />
          </div>

          {/* Selected Members Table */}
          {committeeMembers.length > 0 && (
            <div>
              <Text weight={500} mb="xs">Selected Members ({committeeMembers.length})</Text>
              <Table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Designation</th>
                    <th>Department</th>
                    <th>PI Eligible</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {committeeMembers.map(member => (
                    <tr key={member.id}>
                      <td>{member.name}</td>
                      <td>{member.designation}</td>
                      <td>{member.department}</td>
                      <td>
                        <Badge color="green">Yes</Badge>
                      </td>
                      <td>
                        <ActionIcon
                          color="red"
                          variant="light"
                          onClick={() => handleRemoveMember(member.id.toString())}
                        >
                          <IconX size={16} />
                        </ActionIcon>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          )}

          <Group>
            <Button
              onClick={handleSubmit}
              loading={loading}
              disabled={selectedMembers.length < 3}
              fullWidth
            >
              Create Committee ({selectedMembers.length}/3+ members)
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Container>
  );
};

// ============================================================================
// 3. COMMITTEE VOTING INTERFACE (UC-008, BR-RSPC-15)
// ============================================================================

export const CommitteeInterface = ({ staffId }) => {
  const [loading, setLoading] = useState(false);
  const [staffData, setStaffData] = useState(null);
  const [verdict, setVerdict] = useState('APPROVE');
  const [comments, setComments] = useState('');
  const [hasConflict, setHasConflict] = useState(false);
  const [conflictReason, setConflictReason] = useState('');

  useEffect(() => {
    loadStaffData();
  }, [staffId]);

  const loadStaffData = async () => {
    try {
      const response = await axios.get(`${API_URL}/staff/${staffId}/`);
      setStaffData(response.data);
    } catch (error) {
      console.error('Failed to load staff data', error);
    }
  };

  const handleSubmitVerdict = async () => {
    if (hasConflict && !conflictReason) {
      Notification.show({
        title: 'Error',
        message: 'BR-RSPC-15: Conflict reason must be provided',
        color: 'red',
      });
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API_URL}/staff/${staffId}/verdict/`, {
        member_id: parseInt(localStorage.getItem('member_id')),
        decision: hasConflict ? null : verdict,
        comments,
        has_conflict_of_interest: hasConflict,
        conflict_reason: conflictReason,
      });

      Notification.show({
        title: 'Success',
        message: hasConflict ? 'Conflict recorded (BR-RSPC-15)' : 'Verdict submitted',
        color: 'green',
      });
      
      loadStaffData();
    } catch (error) {
      Notification.show({
        title: 'Error',
        message: error.response?.data?.error || 'Failed to submit verdict',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  if (!staffData) {
    return <Loading />;
  }

  return (
    <Container>
      <Paper p="md" shadow="sm" withBorder>
        <Title order={2} mb="md">Committee Verdict (UC-008)</Title>

        <Alert icon={<IconAlertCircle />} color="yellow" mb="md">
          BR-RSPC-15: Conflict of Interest Declaration
        </Alert>

        <Stack spacing="md">
          {/* Staff Details */}
          <Card withBorder>
            <Stack spacing="sm">
              <Group>
                <Text weight={500}>Position:</Text>
                <Text>{staffData.type_display}</Text>
              </Group>
              <Group>
                <Text weight={500}>Candidate:</Text>
                <Text>{staffData.person}</Text>
              </Group>
              <Group>
                <Text weight={500}>Status:</Text>
                <Badge>{staffData.approval_status_display}</Badge>
              </Group>
            </Stack>
          </Card>

          <Divider />

          {/* Conflict of Interest Section */}
          <div>
            <Checkbox
              label="I have a conflict of interest (BR-RSPC-15)"
              checked={hasConflict}
              onChange={(e) => {
                setHasConflict(e.currentTarget.checked);
                if (e.currentTarget.checked) setVerdict(null);
              }}
              mb="md"
            />

            {hasConflict && (
              <Textarea
                label="Conflict Reason"
                placeholder="Explain the conflict of interest"
                value={conflictReason}
                onChange={(e) => setConflictReason(e.currentTarget.value)}
                required
                mb="md"
              />
            )}
          </div>

          {/* Verdict Selection */}
          {!hasConflict && (
            <div>
              <Text weight={500} mb="xs">Your Decision</Text>
              <Group mb="md">
                <Button
                  variant={verdict === 'APPROVE' ? 'filled' : 'light'}
                  color="green"
                  onClick={() => setVerdict('APPROVE')}
                >
                  <IconCheck size={16} /> Approve
                </Button>
                <Button
                  variant={verdict === 'REJECT' ? 'filled' : 'light'}
                  color="red"
                  onClick={() => setVerdict('REJECT')}
                >
                  <IconX size={16} /> Reject
                </Button>
                <Button
                  variant={verdict === 'ABSTAIN' ? 'filled' : 'light'}
                  color="gray"
                  onClick={() => setVerdict('ABSTAIN')}
                >
                  <IconClock size={16} /> Abstain
                </Button>
              </Group>
            </div>
          )}

          {/* Comments */}
          <Textarea
            label="Comments"
            placeholder="Add any comments or recommendations"
            value={comments}
            onChange={(e) => setComments(e.currentTarget.value)}
          />

          <Button
            onClick={handleSubmitVerdict}
            loading={loading}
            fullWidth
            color={hasConflict ? 'yellow' : verdict === 'APPROVE' ? 'green' : 'red'}
          >
            {hasConflict ? 'Record Conflict' : 'Submit Verdict'}
          </Button>
        </Stack>
      </Paper>
    </Container>
  );
};

// ============================================================================
// 4. STAFF WORKFLOW TRACKER (Status Visualization)
// ============================================================================

export const StaffWorkflowTracker = ({ staffId }) => {
  const [workflow, setWorkflow] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkflow();
  }, [staffId]);

  const loadWorkflow = async () => {
    try {
      const response = await axios.get(`${API_URL}/staff/${staffId}/workflow/`);
      setWorkflow(response.data);
    } catch (error) {
      console.error('Failed to load workflow', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !workflow) {
    return <Loading />;
  }

  const stages = [
    { status: 'DRAFT', label: 'Request Created', icon: '📝' },
    { status: 'COMMITTEE_PENDING', label: 'Committee Review', icon: '👥' },
    { status: 'COMMITTEE_APPROVED', label: 'Committee Approved', icon: '✓' },
    { status: 'HOD_PENDING', label: 'HOD Review', icon: '👔' },
    { status: 'HOD_APPROVED', label: 'HOD Approved', icon: '✓' },
    { status: 'RSPC_PENDING', label: 'RSPC Review', icon: '⚙️' },
    { status: 'APPOINTED', label: 'Appointed', icon: '🎉' },
  ];

  const currentIndex = stages.findIndex(s => s.status === workflow.current_stage);

  return (
    <Paper p="md" shadow="sm" withBorder>
      <Title order={3} mb="md">Workflow Status</Title>

      <Group mb="md">
        <Badge size="lg" color="blue">{workflow.stage_display}</Badge>
        <Text size="sm" color="dimmed">Approver: {workflow.current_approver}</Text>
      </Group>

      <Timeline active={currentIndex} bulletSize={24} lineWidth={2}>
        {stages.map((stage, index) => (
          <Timeline.Item
            key={stage.status}
            bullet={stage.icon}
            title={stage.label}
            color={index <= currentIndex ? 'blue' : 'gray'}
          >
            <Text size="sm" color={index <= currentIndex ? 'black' : 'dimmed'}>
              {index <= currentIndex ? 'Completed' : 'Pending'}
            </Text>
          </Timeline.Item>
        ))}
      </Timeline>

      <Divider my="md" />

      <Text weight={500} mb="sm">Next Step</Text>
      <Alert icon={<IconAlertCircle />} color="info">
        {workflow.next_step}
      </Alert>
    </Paper>
  );
};

// ============================================================================
// 5. APPROVAL INTERFACES (HOD/RSPC Admin)
// ============================================================================

export const ApprovalInterfaces = ({ staffId, userRole }) => {
  const [loading, setLoading] = useState(false);
  const [staffData, setStaffData] = useState(null);
  const [action, setAction] = useState('APPROVE');
  const [comments, setComments] = useState('');
  const [approvalReason, setApprovalReason] = useState('');

  useEffect(() => {
    loadStaffData();
  }, [staffId]);

  const loadStaffData = async () => {
    try {
      const response = await axios.get(`${API_URL}/staff/${staffId}/`);
      setStaffData(response.data);
    } catch (error) {
      console.error('Failed to load staff data', error);
    }
  };

  const handleApproval = async (endpoint) => {
    if (!comments) {
      Notification.show({
        title: 'Error',
        message: 'Comments are required',
        color: 'red',
      });
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API_URL}/staff/${staffId}/${endpoint}/`, {
        action,
        comments,
      });

      Notification.show({
        title: 'Success',
        message: `${action} recorded successfully`,
        color: 'green',
      });

      loadStaffData();
    } catch (error) {
      Notification.show({
        title: 'Error',
        message: error.response?.data?.error || 'Failed to record approval',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  if (!staffData) {
    return <Loading />;
  }

  return (
    <Container>
      <Paper p="md" shadow="sm" withBorder>
        <Title order={2} mb="md">
          {userRole === 'hod' ? 'HOD Approval' : 'RSPC Admin Approval'}
        </Title>

        <Stack spacing="md">
          <Card withBorder>
            <Stack spacing="sm">
              <Group>
                <Text weight={500}>Position:</Text>
                <Text>{staffData.type_display}</Text>
              </Group>
              <Group>
                <Text weight={500}>Candidate:</Text>
                <Text>{staffData.person}</Text>
              </Group>
              <Group>
                <Text weight={500}>Status:</Text>
                <Badge>{staffData.approval_status_display}</Badge>
              </Group>
            </Stack>
          </Card>

          <Divider />

          <Group>
            <Button
              variant={action === 'APPROVE' ? 'filled' : 'light'}
              color="green"
              onClick={() => setAction('APPROVE')}
            >
              <IconCheck size={16} /> Approve
            </Button>
            <Button
              variant={action === 'REJECT' ? 'filled' : 'light'}
              color="red"
              onClick={() => setAction('REJECT')}
            >
              <IconX size={16} /> Reject
            </Button>
          </Group>

          <Textarea
            label="Comments"
            placeholder="Provide your remarks and decision reasons"
            value={comments}
            onChange={(e) => setComments(e.currentTarget.value)}
            required
          />

          <Button
            onClick={() =>
              handleApproval(userRole === 'hod' ? 'hod-approve' : 'rspc-approve')
            }
            loading={loading}
            fullWidth
            color={action === 'APPROVE' ? 'green' : 'red'}
          >
            {action} Staff Appointment
          </Button>
        </Stack>
      </Paper>
    </Container>
  );
};

export default {
  StaffRequestForm,
  CommitteeSelection,
  CommitteeInterface,
  StaffWorkflowTracker,
  ApprovalInterfaces,
};
