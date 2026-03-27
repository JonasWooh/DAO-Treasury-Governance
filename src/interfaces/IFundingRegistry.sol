// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IFundingRegistry {
    enum ProposalStatus {
        Submitted,
        Voting,
        Approved,
        Rejected,
        Cancelled
    }

    enum MilestoneState {
        Locked,
        OpenForClaim,
        ClaimSubmitted,
        ClaimRejected,
        Released
    }

    enum ProjectStatus {
        Active,
        Completed,
        Cancelled
    }

    struct Member {
        address account;
        bool isRegistered;
        bool isActive;
        uint256 currentReputation;
    }

    struct Proposal {
        uint256 proposalId;
        address proposer;
        address recipient;
        string title;
        string metadataURI;
        uint256 requestedFundingWeth;
        uint8 milestoneCount;
        ProposalStatus status;
        uint256 governorProposalId;
        bytes32 projectId;
    }

    struct Milestone {
        uint8 index;
        string description;
        uint256 amountWeth;
        string evidenceURI;
        MilestoneState state;
        uint256 claimGovernorProposalId;
    }

    struct Project {
        bytes32 projectId;
        uint256 sourceProposalId;
        address recipient;
        uint256 approvedBudgetWeth;
        uint256 releasedWeth;
        uint8 nextClaimableMilestone;
        ProjectStatus status;
    }

    function submitProposal(
        string calldata title,
        string calldata metadataURI,
        address recipient,
        uint256 requestedFundingWeth,
        string[] calldata milestoneDescriptions,
        uint256[] calldata milestoneAmountsWeth
    ) external returns (uint256 proposalId);

    function linkGovernorProposal(uint256 proposalId, uint256 governorProposalId) external;

    function linkMilestoneGovernorProposal(
        uint256 proposalId,
        uint8 milestoneIndex,
        uint256 governorProposalId
    ) external;

    function markProposalApproved(uint256 proposalId, bytes32 projectId) external;

    function markProposalRejected(uint256 proposalId) external;

    function cancelProposal(uint256 proposalId) external;

    function submitMilestoneClaim(uint256 proposalId, uint8 milestoneIndex, string calldata evidenceURI) external;

    function markMilestoneRejected(uint256 proposalId, uint8 milestoneIndex) external;

    function markMilestoneReleased(uint256 proposalId, uint8 milestoneIndex) external;

    function finalizeProposalOutcome(uint256 proposalId) external;

    function finalizeMilestoneOutcome(uint256 proposalId, uint8 milestoneIndex) external;

    function settleVoteParticipationBatch(uint256 proposalId, address[] calldata voters) external;

    function settleMilestoneVoteParticipationBatch(
        uint256 proposalId,
        uint8 milestoneIndex,
        address[] calldata voters
    ) external;

    function deriveProjectId(uint256 proposalId, address proposer, address recipient) external pure returns (bytes32);

    function getProposal(uint256 proposalId) external view returns (Proposal memory);

    function getProposalByIndex(uint256 index) external view returns (Proposal memory);

    function proposalCount() external view returns (uint256);

    function getProject(bytes32 projectId) external view returns (Project memory);

    function getProjectByIndex(uint256 index) external view returns (Project memory);

    function projectCount() external view returns (uint256);

    function getMilestone(uint256 proposalId, uint8 milestoneIndex) external view returns (Milestone memory);

    function milestoneCount(uint256 proposalId) external view returns (uint256);

    function getMember(address member) external view returns (Member memory);

    function getMemberByIndex(uint256 index) external view returns (Member memory);

    function memberCount() external view returns (uint256);

    function hasVoteParticipationSettled(uint256 proposalId, address voter) external view returns (bool);

    function hasMilestoneVoteParticipationSettled(
        uint256 proposalId,
        uint8 milestoneIndex,
        address voter
    ) external view returns (bool);
}
