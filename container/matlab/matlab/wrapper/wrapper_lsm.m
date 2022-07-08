function wrapper_lsm(file)

myVars = {'K','Ct','offset'};
data = load(file,myVars{:});
offset = data.offset;
K_orig = data.K; % original cost matrix

Ct = data.Ct;
[n1,n2] = size(Ct);
K = - data.K;
%%% Set infeasible assignments to -infinity
%for i=1:n1*n2
%  if Ct(i)==0
%    K(i,i) = - 1e15;
%  end
%end

tstart = tic;
fprintf('Start optimization: \n')
fprintf('Model: n1: %g n2: %g \n', n1, n2)

assign = my_lsm(K, Ct, []);

X = assign.X
X = discretisationMatching_hungarian(full(X),Ct);


curr_score = X(:)' * K_orig * X(:);

fprintf('time: %f ',toc(tstart))
fprintf('upper_bound: %f ', full(curr_score)+cast(offset,'like',full(curr_score)))
indices = 1:n2;
matching = reshape(X,size(Ct))*indices';
fprintf('labeling: [')
fprintf('%g,',matching(1:end-1))
fprintf('%g] \n',matching(end))


function assign = my_lsm(K, Ct, asgT, options)
    %
    %Graph Matching via Local Sparse Model
    %Reference: @paper{AAAI159386,
    % 	author = {Bo Jiang and Jin Tang and Chris Ding and Bin Luo},
    % 	title = {A Local Sparse Model for Matching Problem},
    % 	conference = {AAAI Conference on Artificial Intelligence},
    % 	year = {2015},
    % 	keywords = {feature matching; sparse model; match selection},
    % 	abstract = {Feature matching problem that incorporates pairwise constraints is usually formulated as a quadratic assignment problem (QAP). Since it is NP-hard, relaxation models are required. In this paper, we first formulate the QAP from the match selection point of view; and then propose a local sparse model for matching problem. Our local sparse matching (LSM) method has the following advantages: (1) It is parameter-free; (2) It generates a local sparse solution which is closer to a discrete matrix than most other continuous relaxation methods for the matching problem. (3) The one-to-one matching constraints are better maintained in LSM solution. Promising experimental results show the effectiveness of the Proposed LSM method.},
    %
    % 	url = {http://www.aaai.org/ocs/index.php/AAAI/AAAI15/paper/view/9386}
    % }
    %
    [n1, n2] = size(Ct);
    num_matches = nnz(Ct);
    %x = ones(NofNodes^2, 1) / NofNodes;
    x = ones(n1*n2,1) / n1;
    % Set assignments with C_{ik}=0 to - infty
    x(Ct==0) = 0;
    bestv = -1e20;
    lambda = -1e20;
    Xast = [];
    for i = 1:10000
        Kx = K * x;
        lastv = lambda;
        lambda = x'*Kx;

        KxMat = reshape(Kx, [n1, n2]);
        Xmat = reshape(x, [n1, n2]);
        SumX = sum(Xmat);
        SumXExpand = ones(n1, 1) * SumX;
        SumXExpand = reshape(SumXExpand, [n1*n2, 1]);
        x = x.*sqrt(Kx./SumXExpand/lambda);

    %    figure(1);imshow(imresize(reshape(x * 255,[NofNodes, NofNodes]),4, 'nearest'), [] );SumXExpand;
     %   fprintf('Iter = %d, relax obj = %12.5f, Obj = %12.5f\n',i,lambda, bestv);
      %  drawnow;
        if(abs(lastv - lambda) < 1e-6)
            break;
            i
        end
    end
    %[IntX, cost] = hungarian(-reshape(x, [n1, n2]));
    %IntX = IntX(:);
    %DecodeObj = IntX' * K * IntX;
    %if(DecodeObj > bestv)
    %    Xast = IntX;
    %    bestv = DecodeObj;
    %end
    assign.X = (reshape(x,[n1,n2]));
    %acc = matchAsg(assign.X , asgT);
    %assign.acc = acc;
    %assign.obj = bestv;
