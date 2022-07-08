function wrappre_ga(file)

myVars = {'K','Ct','reducedK','offset'};
data = load(file,myVars{:});
offset = data.offset;
K_orig = data.K; % original cost matrix

Ct = data.Ct;
[n1,n2] = size(Ct);
K = - data.reducedK;

% function parameter
b0 =  max(n1, n2);
b0 = 0.5;
bStep =  1.075;
bMax =  200;
tolB = 1e-3;
tolC = 1e-3;
maxBIters = 1000;
nthIter = 200;


tstart = tic;
fprintf('Start optimization: \n')
fprintf('Model: n1: %g n2: %g \n', n1, n2)

[X,nbMatVec] = gradAssign(K, Ct, b0, bStep, bMax, tolB, tolC);
X = discretisationMatching_hungarian(full(X),Ct);

curr_score = X(:)' * K_orig * X(:);

fprintf('time: %f ',toc(tstart))
fprintf('upper_bound: %f ', full(curr_score) + cast(offset,'like',full(curr_score)))
indices = 1:n2;
matching = reshape(X,size(Ct))*indices';
fprintf('labeling: [')
fprintf('%g,',matching(1:end-1))
fprintf('%g] \n',matching(end))

%squit force;
